from fastapi import APIRouter, HTTPException, Query
import psycopg
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
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

    tz = ZoneInfo("Europe/Lisbon")      # Force the local Porto timezone
    now = datetime.now(tz)    # Get current time in HH:MM:SS format for GTFS comparison

    future_limit_hours = 2  # How many hours into the future we want to look for arrivals

    if now.hour < 2 and now.hour < 24 - future_limit_hours:
        # If it's between midnight and 2 AM, we need to check the previous day's service
        # The "M" nightline services run every day with the same schedule, so this assumption is ok.
        current_date_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        current_time_str = f"{now.hour + 24}:{now.strftime('%M:%S')}"
        two_hours_later_str = f"{now.hour + 24 + future_limit_hours}:{now.strftime('%M:%S')}"

    elif now.hour >= 24 - future_limit_hours:
        current_date_str = now.strftime("%Y-%m-%d")
        current_time_str = f"{now.hour}:{now.strftime('%M:%S')}"
        two_hours_later_str = f"{now.hour + future_limit_hours}:{now.strftime('%M:%S')}"
        
    else:
        current_date_str = now.strftime("%Y-%m-%d")
        current_time_str = now.strftime("%H:%M:%S")
        two_hours_later_str = (now + timedelta(hours=future_limit_hours)).strftime("%H:%M:%S")

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
                
                cur.execute(query, (stop_id, current_date_str, route_short_name, route_short_name, 
                                    current_time_str, two_hours_later_str))
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