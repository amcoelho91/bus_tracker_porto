from fastapi import APIRouter, HTTPException, Query
import psycopg
import os
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter()
DATABASE_URL = os.environ["DATABASE_URL"]

class VehicleHistory(BaseModel):
    vehicle_id: str
    observed_at: datetime
    route_id: str
    direction: int
    trip_id: Optional[str]
    trip_headsign: Optional[str]
    lat: float
    lon: float
    last_stop_id: Optional[str]
    last_stop_name: Optional[str]
    cur_stop_id: Optional[str]
    route_short_name: Optional[str]
    route_long_name: Optional[str]

@router.get("/history", response_model=List[VehicleHistory])
async def get_vehicle_history(
    mode: str = Query(..., regex="^(trip|route)$"),
    route_id: str = Query(...),
    date: str = Query(...), # Format: YYYY-MM-DD
    trip_id: Optional[str] = Query(None),
    start_time: Optional[str] = Query("00:00"),
    end_time: Optional[str] = Query("23:59")
):
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # # Base Query
                # base_sql = """
                #     SELECT 
                #         vehicle_id, observed_at, route_id, direction, trip_id,
                #         ST_Y(geom::geometry) as lat, ST_X(geom::geometry) as lon,
                #         last_stop_id, last_stop_name, cur_stop_id
                #     FROM bus.vehicle_observation
                #     WHERE route_id = %s AND observed_at::date = %s
                # """
                # Base Query
                base_sql = """
                    SELECT 
                        o.vehicle_id, o.observed_at, o.route_id, o.direction, o.trip_id, t.trip_headsign,
                        ST_Y(o.geom::geometry) as lat, ST_X(o.geom::geometry) as lon,
                        o.last_stop_id, s.stop_name, o.cur_stop_id, r.route_short_name, r.route_long_name
                    FROM bus.vehicle_observation o
                    LEFT JOIN gtfs.routes r ON o.route_id = r.route_id
                    LEFT JOIN gtfs.stops s ON o.last_stop_id = s.stop_id
                    LEFT JOIN gtfs.trips t ON o.trip_id = t.trip_id
                    WHERE o.route_id = %s AND o.observed_at::date = %s
                """
                
                params = [route_id, date]

                if mode == "trip" and trip_id:
                    base_sql += " AND o.trip_id = %s"
                    params.append(trip_id)
                else:
                    base_sql += " AND o.observed_at::time >= %s AND o.observed_at::time <= %s"
                    params.extend([start_time or "00:00", end_time or "23:59"])

                base_sql += " ORDER BY o.observed_at ASC LIMIT 2000"

                cur.execute(base_sql, params)
                rows = cur.fetchall()

                return [
                    VehicleHistory(
                        vehicle_id=row[0],
                        observed_at=row[1],
                        route_id=row[2],
                        direction=row[3],
                        trip_id=row[4],
                        trip_headsign=row[5],
                        lat=row[6],
                        lon=row[7],
                        last_stop_id=row[8],
                        last_stop_name=row[9],
                        cur_stop_id=row[10],
                        route_short_name=row[11],
                        route_long_name=row[12]
                    ) for row in rows
                ]

    except Exception as e:
        print(f"History Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/trips-list")
async def get_trips_with_data(
    route_id: str = Query(...),
    date: str = Query(...)
):
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Get unique trips for this route/day that have observations
                cur.execute("""
                    SELECT DISTINCT trip_id 
                    FROM bus.vehicle_observation 
                    WHERE route_id = %s 
                        AND CAST(observed_at AT TIME ZONE 'UTC' AS DATE) = %s
                        AND trip_id IS NOT NULL
                    ORDER BY trip_id ASC
                """, (route_id, date))
                
                rows = cur.fetchall()
                return [row[0] for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

class TripExecution(BaseModel):
    trip_id: str
    vehicle_id: Optional[str] = None
    real_stop_id: Optional[str] = None
    real_arrival_time: Optional[datetime] = None
    estimated_arrival_time: Optional[datetime] = None
    planned_stop_id: str
    planned_stop_name: str
    planned_arrival_time: str


@router.get("/history/trip-execution", response_model=List[TripExecution])
async def get_trip_execution(
    trip_id: str = Query(...),
    date: str = Query(...)
):
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # cur.execute("""
                #     WITH trip_identity AS (
                #         -- Step 1: Identify the ONE vehicle that ran this trip
                #         SELECT vehicle_id
                #         FROM bus.vehicle_observation
                #         WHERE trip_id = %s 
                #           AND observed_at::date = %s::date
                #           AND vehicle_id IS NOT NULL
                #         LIMIT 1
                #     ),
                #     unique_observations AS (
                #         -- Step 2: Get the first arrival at each stop for ONLY that vehicle
                #         SELECT DISTINCT ON (cur_stop_id)
                #             cur_stop_id,
                #             observed_at
                #         FROM bus.vehicle_observation
                #         WHERE trip_id = %s 
                #           AND observed_at::date = %s::date
                #           AND vehicle_id = (SELECT vehicle_id FROM trip_identity)
                #           AND cur_stop_id IS NOT NULL
                #         ORDER BY cur_stop_id, observed_at ASC
                #     )
                #     SELECT 
                #         st.trip_id,
                #         (SELECT vehicle_id FROM trip_identity) as vehicle_id,
                #         uo.cur_stop_id AS real_stop_id, 
                #         uo.observed_at AS real_arrival_time, 
                #         st.stop_id AS planned_stop_id, 
                #         s.stop_name AS planned_stop_name, 
                #         st.arrival_time AS planned_arrival_time
                #     FROM gtfs.stop_times st
                #     JOIN gtfs.stops s ON st.stop_id = s.stop_id
                #     LEFT JOIN unique_observations uo ON st.stop_id = uo.cur_stop_id
                #     WHERE st.trip_id = %s
                #     ORDER BY st.stop_sequence ASC
                # """, (trip_id, date, trip_id, date, trip_id))
                cur.execute("""
                    WITH trip_identity AS (
                        -- Get vehicle and the shape geometry for this specific trip
                        SELECT vo.vehicle_id, t.shape_id, s.geom as shape_geom
                        FROM bus.vehicle_observation vo
                        JOIN gtfs.trips t ON vo.trip_id = t.trip_id
                        JOIN gtfs.shapes s ON t.shape_id = s.shape_id
                        WHERE vo.trip_id = %s 
                        AND vo.observed_at::date = %s::date
                        AND vo.vehicle_id IS NOT NULL
                        LIMIT 1
                    ),
                    all_pings AS (
                        -- Get every ping for this vehicle today, mapped as fractions (0-1) along the shape
                        SELECT 
                            vo.observed_at,
                            ST_LineLocatePoint(ti.shape_geom, vo.geom) as fraction
                        FROM bus.vehicle_observation vo
                        JOIN trip_identity ti ON vo.vehicle_id = ti.vehicle_id
                        WHERE vo.trip_id = %s 
                        AND vo.observed_at::date = %s::date
                        -- Within 50 meters constraint
                        AND ST_DWithin(vo.geom::geography, ti.shape_geom::geography, 50)
                    ),
                    stop_distances AS (
                        -- Get the planned stop distances converted to fractions
                        SELECT 
                            ss.stop_id,
                            ss.stop_sequence,
                            ss.shape_dist_traveled / NULLIF(MAX(ss.shape_dist_traveled) OVER(), 0) as stop_frac
                        FROM gtfs.shape_stops ss
                        JOIN trip_identity ti ON ss.shape_id = ti.shape_id
                    ),
                    interpolated_times AS (
                        -- For every stop, find the closest ping BEFORE and AFTER
                        SELECT 
                            sd.stop_id,
                            sd.stop_sequence,
                            (SELECT MAX(observed_at) FROM all_pings p WHERE p.fraction <= sd.stop_frac) as ping_a_time,
                            (SELECT MIN(observed_at) FROM all_pings p WHERE p.fraction > sd.stop_frac) as ping_b_time,
                            (SELECT MAX(fraction) FROM all_pings p WHERE p.fraction <= sd.stop_frac) as ping_a_frac,
                            (SELECT MIN(fraction) FROM all_pings p WHERE p.fraction > sd.stop_frac) as ping_b_frac
                        FROM stop_distances sd
                    ),
                    unique_observations AS (
                        SELECT DISTINCT ON (cur_stop_id) cur_stop_id, observed_at
                        FROM bus.vehicle_observation
                        WHERE trip_id = %s AND observed_at::date = %s::date
                        AND vehicle_id = (SELECT vehicle_id FROM trip_identity)
                        AND cur_stop_id IS NOT NULL
                        ORDER BY cur_stop_id, observed_at ASC
                    )
                    SELECT 
                        st.trip_id,
                        ti.vehicle_id,
                        uo.cur_stop_id AS real_stop_id, 
                        uo.observed_at AS real_arrival_time, 
                        st.stop_id AS planned_stop_id, 
                        s.stop_name AS planned_stop_name, 
                        st.arrival_time AS planned_arrival_time,
                        -- THE ESTIMATION LOGIC
                        CASE 
                            -- If we have a real arrival, use that
                            WHEN uo.observed_at IS NOT NULL THEN uo.observed_at
                            -- If gap is < 2.5 minutes, interpolate
                            WHEN (it.ping_b_time - it.ping_a_time) < interval '2.5 minutes' THEN
                                it.ping_a_time + (it.ping_b_time - it.ping_a_time) * ((si.stop_frac - it.ping_a_frac) / NULLIF(it.ping_b_frac - it.ping_a_frac, 0))
                            ELSE NULL
                        END as estimated_arrival_time
                    FROM gtfs.stop_times st
                    JOIN gtfs.stops s ON st.stop_id = s.stop_id
                    CROSS JOIN trip_identity ti
                    LEFT JOIN stop_distances si ON st.stop_id = si.stop_id AND st.stop_sequence = si.stop_sequence
                    LEFT JOIN interpolated_times it ON st.stop_id = it.stop_id AND st.stop_sequence = it.stop_sequence
                    LEFT JOIN unique_observations uo ON st.stop_id = uo.cur_stop_id
                    WHERE st.trip_id = %s
                    ORDER BY st.stop_sequence ASC
                """, (trip_id, date, trip_id, date, trip_id, date, trip_id))


                # If no observations found, trip_identity might be empty. 
                # In that case, it returns the planned schedule.
                rows = cur.fetchall()
                return [
                    TripExecution(
                        trip_id=row[0],
                        vehicle_id=row[1],
                        real_stop_id=row[2],
                        real_arrival_time=row[3],
                        planned_stop_id=row[4],
                        planned_stop_name=row[5],
                        planned_arrival_time=row[6],
                        estimated_arrival_time=row[7],
                    ) for row in rows
                ]
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))