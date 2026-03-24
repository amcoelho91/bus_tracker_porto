import os
import time
import requests
import psycopg
from datetime import datetime, timezone

from worker.parse import parse_annotations, get_value, extract_lon_lat

DATABASE_URL = os.environ["DATABASE_URL"]
FIWARE_URL = os.environ["FIWARE_URL"]
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "60"))

def iso_to_dt(s: str) -> datetime:
    # FIWARE often returns e.g. "2025-10-01T12:34:56.000Z"
    # Replace Z for fromisoformat
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

def ensure_db_ready():
    # DB schema is created by docker-entrypoint-initdb.d on first startup.
    # This function just checks we can connect.
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")

def main():
    ensure_db_ready()

    while True:
        started = datetime.now(timezone.utc)
        status = "success"
        error_message = None
        fetched = 0
        inserted_obs = 0
        updated_latest = 0

        try:
            r = requests.get(FIWARE_URL, timeout=30)
            r.raise_for_status()
            entities = r.json()
            fetched = len(entities)

            with psycopg.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    for e in entities:
                        vehicle_id = e["id"]
                        fleet_vehicle_id = get_value(e, "fleetVehicleId")
                        name = get_value(e, "name")
                        data_provider = get_value(e, "dataProvider")
                        vehicle_type = get_value(e, "vehicleType")
                        source = get_value(e, "source")

                        observed_at_raw = get_value(e, "observationDateTime")
                        if not observed_at_raw:
                            continue
                        observed_at = iso_to_dt(observed_at_raw)

                        ann_values = (e.get("annotations") or {}).get("value")
                        ann = parse_annotations(ann_values)
                        route_id = ann.get("stcp:route")
                        trip_id = ann.get("stcp:nr_viagem")
                        direction_raw = ann.get("stcp:sentido")
                        direction = int(direction_raw) if direction_raw and direction_raw.isdigit() else None

                        lon, lat = extract_lon_lat(e)

                        speed = get_value(e, "speed")
                        bearing = get_value(e, "bearing")
                        heading = get_value(e, "heading")
                        current_trip_count = get_value(e, "currentTripCount")

                        # Upsert vehicle
                        cur.execute(
                            """
                            INSERT INTO bus.vehicle(vehicle_id, fleet_vehicle_id, name, data_provider, vehicle_type, source)
                            VALUES (%s,%s,%s,%s,%s,%s)
                            ON CONFLICT (vehicle_id) DO UPDATE
                            SET fleet_vehicle_id = EXCLUDED.fleet_vehicle_id,
                                name = EXCLUDED.name,
                                data_provider = EXCLUDED.data_provider,
                                vehicle_type = EXCLUDED.vehicle_type,
                                source = EXCLUDED.source,
                                updated_at = now()
                            """,
                            (vehicle_id, fleet_vehicle_id, name, data_provider, vehicle_type, source),
                        )

                        # # Insert history (dedupe if unique index exists)
                        # cur.execute(
                        #     """
                        #     WITH shape_lookup AS (
                        #         -- Get the shape for this route and direction
                        #         SELECT shape_id, geom as shape_geom 
                        #         FROM gtfs.shapes 
                        #         WHERE route_id = %s AND direction_id = %s 
                        #         LIMIT 1
                        #     ),
                        #     matched_stop AS (
                        #         -- Perform the math we tested in the standalone script
                        #         SELECT ss.stop_id
                        #         FROM shape_lookup sl
                        #         JOIN gtfs.shape_stops ss ON sl.shape_id = ss.shape_id
                        #         JOIN gtfs.stops s ON ss.stop_id = s.stop_id
                        #         WHERE 
                        #             -- Distance check: must be within 150 meters
                        #             ST_Distance(ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, sl.shape_geom::geography) < 150
                        #             -- Sequence check: stop must be 'behind' or 'at' the bus
                        #             AND ST_LineLocatePoint(sl.shape_geom, ST_SetSRID(ST_MakePoint(s.stop_lon, s.stop_lat), 4326)) 
                        #                 <= (ST_LineLocatePoint(sl.shape_geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) + 0.002)
                        #         ORDER BY ss.stop_sequence DESC
                        #         LIMIT 1
                        #     )
                        #     INSERT INTO bus.vehicle_observation(
                        #     vehicle_id, observed_at, route_id, direction, trip_id,
                        #     speed, bearing, heading, current_trip_count, geom, last_stop_id
                        #     )
                        #     VALUES (
                        #     %s, %s, %s, %s, %s,
                        #     %s, %s, %s, %s,
                        #     ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                        #     (SELECT stop_id FROM matched_stop)
                        #     )
                        #     ON CONFLICT DO NOTHING;
                        #     """,
                        #     (
                        #         route_id, direction, # For shape lookup
                        #         lon, lat,            # For Distance check
                        #         lon, lat,            # For LineLocate check
                        #         vehicle_id, observed_at, route_id, direction, trip_id,
                        #         speed, bearing, heading, current_trip_count, lon, lat
                        #     ),
                        # )
                        cur.execute(
                            """
                            INSERT INTO bus.vehicle_observation(
                              vehicle_id, observed_at, route_id, direction, trip_id,
                              speed, bearing, heading, current_trip_count, geom
                            )
                            VALUES (
                              %s,%s,%s,%s,%s,
                              %s,%s,%s,%s,
                              ST_SetSRID(ST_MakePoint(%s,%s), 4326)
                            )
                            ON CONFLICT DO NOTHING
                            """,
                            (
                                vehicle_id, observed_at, route_id, direction, trip_id,
                                speed, bearing, heading, current_trip_count, lon, lat
                            ),
                        )
                        inserted_obs += cur.rowcount  # 1 or 0

                        # Upsert latest (only if newer)
                        # cur.execute(
                        # """
                        #     WITH shape_lookup AS (
                        #         -- Get the shape for this route and direction
                        #         SELECT shape_id, geom as shape_geom 
                        #         FROM gtfs.shapes 
                        #         WHERE route_id = %s AND direction_id = %s 
                        #         LIMIT 1
                        #     ),
                        #     matched_stop AS (
                        #         -- Perform the math we tested in the standalone script
                        #         SELECT ss.stop_id
                        #         FROM shape_lookup sl
                        #         JOIN gtfs.shape_stops ss ON sl.shape_id = ss.shape_id
                        #         JOIN gtfs.stops s ON ss.stop_id = s.stop_id
                        #         WHERE 
                        #             -- Distance check: must be within 150 meters
                        #             ST_Distance(ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, sl.shape_geom::geography) < 150
                        #             -- Sequence check: stop must be 'behind' or 'at' the bus
                        #             AND ST_LineLocatePoint(sl.shape_geom, ST_SetSRID(ST_MakePoint(s.stop_lon, s.stop_lat), 4326)) 
                        #                 <= (ST_LineLocatePoint(sl.shape_geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) + 0.002)
                        #         ORDER BY ss.stop_sequence DESC
                        #         LIMIT 1
                        #     )
                        #     INSERT INTO bus.vehicle_latest AS v(
                        #       vehicle_id, observed_at, fleet_vehicle_id, route_id, direction, trip_id,
                        #       speed, bearing, heading, geom, updated_at, last_stop_id
                        #     )
                        #     VALUES (
                        #       %s,%s,%s,%s,%s,%s,
                        #       %s,%s,%s,
                        #       ST_SetSRID(ST_MakePoint(%s,%s), 4326),
                        #       now(),
                        #       (SELECT stop_id FROM matched_stop)
                        #     )
                        #     ON CONFLICT (vehicle_id) DO UPDATE
                        #     SET observed_at = EXCLUDED.observed_at,
                        #         fleet_vehicle_id = EXCLUDED.fleet_vehicle_id,
                        #         route_id = EXCLUDED.route_id,
                        #         direction = EXCLUDED.direction,
                        #         trip_id = EXCLUDED.trip_id,
                        #         speed = EXCLUDED.speed,
                        #         bearing = EXCLUDED.bearing,
                        #         heading = EXCLUDED.heading,
                        #         geom = EXCLUDED.geom,
                        #         updated_at = now(),
                        #         last_stop_id = EXCLUDED.last_stop_id
                        #     WHERE EXCLUDED.observed_at > v.observed_at
                        #     """,
                        #     (
                        #         vehicle_id, observed_at, fleet_vehicle_id, route_id, direction, trip_id,
                        #         speed, bearing, heading, lon, lat
                        #     ),
                        # )
                        cur.execute(
                            """
                            INSERT INTO bus.vehicle_latest AS v(
                              vehicle_id, observed_at, fleet_vehicle_id, route_id, direction, trip_id,
                              speed, bearing, heading, geom, updated_at
                            )
                            VALUES (
                              %s,%s,%s,%s,%s,%s,
                              %s,%s,%s,
                              ST_SetSRID(ST_MakePoint(%s,%s), 4326),
                              now()
                            )
                            ON CONFLICT (vehicle_id) DO UPDATE
                            SET observed_at = EXCLUDED.observed_at,
                                fleet_vehicle_id = EXCLUDED.fleet_vehicle_id,
                                route_id = EXCLUDED.route_id,
                                direction = EXCLUDED.direction,
                                trip_id = EXCLUDED.trip_id,
                                speed = EXCLUDED.speed,
                                bearing = EXCLUDED.bearing,
                                heading = EXCLUDED.heading,
                                geom = EXCLUDED.geom,
                                updated_at = now()
                            WHERE EXCLUDED.observed_at > v.observed_at
                            """,
                            (
                                vehicle_id, observed_at, fleet_vehicle_id, route_id, direction, trip_id,
                                speed, bearing, heading, lon, lat
                            ),
                        )
                        updated_latest += cur.rowcount  # 1 if updated/inserted, 0 if older

                conn.commit()

        except Exception as e:
            status = "error"
            error_message = str(e)

        finally:
            finished = datetime.now(timezone.utc)
            # optional ingest run log (won't break if table missing)
            try:
                with psycopg.connect(DATABASE_URL) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO bus.ingest_run(started_at, finished_at, status, fetched_count, inserted_obs_count, updated_latest_count, error_message)
                            VALUES (%s,%s,%s,%s,%s,%s,%s)
                            """,
                            (started, finished, status, fetched, inserted_obs, updated_latest, error_message),
                        )
                    conn.commit()
            except Exception:
                pass

        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()