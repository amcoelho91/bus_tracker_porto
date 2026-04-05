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
    lat: float
    lon: float
    last_stop_id: Optional[str]
    cur_stop_id: Optional[str]

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
                
                # Base Query
                base_sql = """
                    SELECT 
                        vehicle_id, observed_at, route_id, direction, trip_id,
                        ST_Y(geom::geometry) as lat, ST_X(geom::geometry) as lon,
                        last_stop_id, cur_stop_id
                    FROM bus.vehicle_observation
                    WHERE route_id = %s AND observed_at::date = %s
                """
                
                params = [route_id, date]

                if mode == "trip" and trip_id:
                    base_sql += " AND trip_id = %s"
                    params.append(trip_id)
                else:
                    base_sql += " AND observed_at::time >= %s AND observed_at::time <= %s"
                    params.extend([start_time or "00:00", end_time or "23:59"])

                base_sql += " ORDER BY observed_at ASC LIMIT 2000"

                cur.execute(base_sql, params)
                rows = cur.fetchall()

                return [
                    VehicleHistory(
                        vehicle_id=row[0],
                        observed_at=row[1],
                        route_id=row[2],
                        direction=row[3],
                        trip_id=row[4],
                        lat=row[5],
                        lon=row[6],
                        last_stop_id=row[7],
                        cur_stop_id=row[8]
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