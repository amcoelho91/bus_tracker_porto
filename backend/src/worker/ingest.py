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
                        vehicle_id = get_value(e, "fleetVehicleId")
                        # name = get_value(e, "name")
                        # data_provider = get_value(e, "dataProvider")
                        # vehicle_type = get_value(e, "vehicleType")
                        # source = get_value(e, "source")

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

                        heading = get_value(e, "heading")
                        current_trip_count = get_value(e, "currentTripCount")

                        # # Insert history (dedupe if unique index exists)
                        cur.execute(
                            """
                            WITH shape_lookup AS (
                                SELECT shape_id, geom as shape_geom,
                                    ST_Length(geom::geography) as total_len 
                                FROM gtfs.shapes 
                                WHERE route_id = %s AND direction_id = %s 
                                LIMIT 1
                            ),
                            bus_geo AS (
                                -- Define the bus point once to reuse
                                SELECT ST_SetSRID(ST_MakePoint(%s, %s), 4326) as geom
                            ),
                            bus_stats AS (
                                -- Calculate how far the bus is ALONG the shape
                                SELECT 
                                    sl.shape_id,
                                    ST_LineLocatePoint(sl.shape_geom, bg.geom) * sl.total_len as bus_dist_m,
                                    ST_Distance(bg.geom::geography, sl.shape_geom::geography) as dist_to_shape
                                FROM shape_lookup sl, bus_geo bg
                            ),
                            matched_last_stop AS (
                                SELECT ss.stop_id 
                                FROM gtfs.shape_stops ss
                                JOIN bus_stats bs ON ss.shape_id = bs.shape_id
                                WHERE 
                                    -- 1. Bus must be near the actual route
                                    bs.dist_to_shape < 150 
                                    -- 2. Use the pre-calculated meters to ensure we are 'behind' the bus
                                    -- This handles circular routes (in theory)
                                    AND ss.shape_dist_traveled <= (bs.bus_dist_m + 10) 
                                ORDER BY ss.stop_sequence DESC
                                LIMIT 1
                            ),
                            matched_current_stop AS (
                                -- Rule: Within 50m of shape, and within 25m physical distance of stop
                                SELECT ss.stop_id
                                FROM gtfs.shape_stops ss
                                JOIN bus_stats bs ON ss.shape_id = bs.shape_id
                                JOIN gtfs.stops s ON ss.stop_id = s.stop_id
                                JOIN bus_geo bg ON TRUE
                                WHERE 
                                    bs.dist_to_shape < 50 -- Stricter off-route check for 'current' stop
                                    AND ABS(ss.shape_dist_traveled - bs.bus_dist_m) < 50 -- Path proximity
                                    AND ST_Distance(bg.geom::geography, ST_SetSRID(ST_MakePoint(s.stop_lon, s.stop_lat), 4326)::geography) < 25 -- Physical proximity
                                ORDER BY ST_Distance(bg.geom::geography, ST_SetSRID(ST_MakePoint(s.stop_lon, s.stop_lat), 4326)::geography) ASC
                                LIMIT 1
                            ),
                            -- 1. Insert into history and RETURNING the values we need
                            inserted_observation AS (
                                INSERT INTO bus.vehicle_observation (
                                    vehicle_id, observed_at, route_id, direction, trip_id,
                                    heading, current_trip_count, geom, last_stop_id, cur_stop_id
                                )
                                SELECT 
                                    %s, %s, %s, %s, %s, %s, %s, bg.geom,
                                    -- If current stop exists, it is also the last stop passed.
                                    COALESCE(
                                            (SELECT stop_id FROM matched_current_stop), 
                                            (SELECT stop_id FROM matched_last_stop)
                                        ),
                                        (SELECT stop_id FROM matched_current_stop)
                                FROM bus_geo bg
                                ON CONFLICT DO NOTHING
                                RETURNING *
                            )
                            -- 2. Upsert the latest table using the data from the insertion above
                            INSERT INTO bus.vehicle_latest AS v (
                                vehicle_id, observed_at, route_id, direction, trip_id,
                                heading, geom, updated_at, last_stop_id, cur_stop_id
                            )
                            SELECT 
                                %s, io.observed_at, io.route_id, io.direction, io.trip_id,
                                io.heading, io.geom, now(), io.last_stop_id, io.cur_stop_id
                            FROM inserted_observation io
                            ON CONFLICT (vehicle_id) DO UPDATE
                            SET 
                                observed_at = EXCLUDED.observed_at,
                                vehicle_id = EXCLUDED.vehicle_id,
                                route_id = EXCLUDED.route_id,
                                direction = EXCLUDED.direction,
                                trip_id = EXCLUDED.trip_id,
                                heading = EXCLUDED.heading,
                                geom = EXCLUDED.geom,
                                updated_at = now(),
                                last_stop_id = EXCLUDED.last_stop_id,
                                cur_stop_id = EXCLUDED.cur_stop_id
                            WHERE EXCLUDED.observed_at > v.observed_at
                            """,
                            (
                                route_id, direction, # for shape lookup
                                lon, lat,            # for bus_geo (distance calculations)
                                vehicle_id, observed_at, route_id, direction, trip_id,
                                heading, current_trip_count, # for inserted_observation
                                vehicle_id  # for vehicle_latest upsert (not from inserted_observation)
                            ),
                        )

                        inserted_obs += cur.rowcount  # 1 or 0

                        updated_latest += cur.rowcount   # 1 if updated/inserted, 0 if older

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