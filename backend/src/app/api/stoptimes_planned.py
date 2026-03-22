from fastapi import APIRouter, HTTPException, Query
import psycopg
import os
from datetime import datetime, timedelta
from typing import List
from pydantic import BaseModel

router = APIRouter()
DATABASE_URL = os.environ["DATABASE_URL"]

class StopArrival(BaseModel):
    route_short_name: str
    arrival_time: str
    trip_headsign: str

@router.get("/arrivals/{stop_id}", response_model=List[StopArrival])
async def get_stop_arrivals(stop_id: str, route_short_name: str = Query(None)):
    stop_id = stop_id.upper()

    now = datetime.now()    # Get current time in HH:MM:SS format for GTFS comparison
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    two_hours_later = (now + timedelta(hours=2)).strftime("%H:%M:%S")

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # 1. Validation: If route_short_name is provided, check if it exists in the database
                if route_short_name:
                    route_short_name = route_short_name.upper()
                    cur.execute("SELECT 1 FROM gtfs.routes WHERE route_short_name = %s", (route_short_name,))
                    if not cur.fetchone():
                        raise HTTPException(status_code=400, detail=f"Route '{route_short_name}' does not exist.")

                # 2. Build the Query with optional filtering by route_short_name
                query = """
                    SELECT 
                        r.route_short_name, 
                        t.trip_headsign,
                        st.arrival_time,
                        t.service_id
                    FROM gtfs.stop_times st
                    JOIN gtfs.trips t ON st.trip_id = t.trip_id
                    JOIN gtfs.routes r ON t.route_id = r.route_id
                    JOIN gtfs.service_by_date sbd ON t.service_id = sbd.service_id
                    WHERE st.stop_id = %s 
                    AND sbd.date = %s
                    AND (%s::TEXT IS NULL OR r.route_short_name = %s)
                    AND st.arrival_time::INTERVAL >= %s::INTERVAL 
                    AND st.arrival_time::INTERVAL <= %s::INTERVAL
                    ORDER BY st.arrival_time::INTERVAL ASC
                    LIMIT 10;
                """
                
                cur.execute(query, (stop_id, current_date, route_short_name, route_short_name, current_time, two_hours_later))
                rows = cur.fetchall()

                return [
                    StopArrival(
                        route_short_name=row[0],
                        trip_headsign=row[1],
                        arrival_time=row[2]
                    ) for row in rows
                ]
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching arrivals: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")