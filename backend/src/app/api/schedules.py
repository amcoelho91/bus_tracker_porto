from fastapi import APIRouter, HTTPException, Query
import psycopg
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List
from pydantic import BaseModel
from collections import defaultdict

router = APIRouter()
DATABASE_URL = os.environ["DATABASE_URL"]

class ScheduledTimetable(BaseModel):
    trip_id: str
    arrival_time: str
    stop_id: str
    stop_name: str
    stop_sequence: int

class ReferenceStop(BaseModel):
    stop_id: str
    stop_name: str
    stop_sequence: int

class TimetableResponse(BaseModel):
    reference_stops: List[ReferenceStop]
    trips: List[ScheduledTimetable]

@router.get("/schedules/daily", response_model=TimetableResponse)
async def get_scheduled_times(
    date: str = Query(...),  # Expects YYYY-MM-DD
    route_id: str = Query(...),
    direction_id: int = Query(0, ge=0, le=1) 
):
    """
    Fetches the planned schedule for a route on a specific date, 
    handling GTFS 24h+ time logic for late-night services.
    """
    tz = ZoneInfo("Europe/Lisbon")
    
    # We parse the requested date. If the user is looking at "today" 
    # during the early AM, we might need to shift the GTFS calendar day.
    try:
        requested_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=tz)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # GTFS Logic: If we are querying for "now" and it's 01:00 AM, 
    # we are technically still on the previous day's service schedule.
    # For a general "Daily Schedule" view, we usually show the date as requested,
    # but we'll keep the variable naming consistent with your arrivals logic.
    current_date_str = requested_date.strftime("%Y-%m-%d")

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # 1A. Validation: Does the route exist?
                cur.execute("SELECT 1 FROM gtfs.routes WHERE route_id = %s", (route_id,))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail=f"Route '{route_id}' not found.")
                
                # 1B. Validation: Are there any services on this date for the route and direction?
                cur.execute("""
                    SELECT 1 FROM gtfs.service_by_date sbd
                    JOIN gtfs.trips t ON sbd.service_id = t.service_id
                    WHERE sbd.date = %s AND t.route_id = %s AND t.direction_id = %s
                """, (current_date_str, route_id, direction_id))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail=f"No services found for route '{route_id}' on {current_date_str} with direction {direction_id}.")

                # 2A. Fetch Reference Columns (Master Route Sequence)
                # We use variant_id = 0 to represent the full route path
                cur.execute("""
                    SELECT DISTINCT ss.stop_id, stops.stop_name, ss.stop_sequence
                    FROM gtfs.shape_stops ss
                    JOIN gtfs.shapes s ON ss.shape_id = s.shape_id
                    JOIN gtfs.stops stops ON ss.stop_id = stops.stop_id
                    WHERE s.route_id = %s 
                        AND s.direction_id = %s 
                        AND s.variant_id = 0
                        AND EXISTS (
                            SELECT 1 FROM gtfs.stop_times st
                            JOIN gtfs.trips t ON st.trip_id = t.trip_id
                            WHERE st.stop_id = ss.stop_id 
                                AND t.route_id = s.route_id 
                                AND st.timepoint = TRUE
                        )
                    ORDER BY ss.stop_sequence ASC
                """, (route_id, direction_id))
                
                ref_rows = cur.fetchall()
                # 2B. If variant 0 doesn't exist, we fallback to any stops associated with the route
                if not ref_rows:
                    cur.execute("""
                        SELECT DISTINCT stop_id, MIN(stop_sequence) as seq
                        FROM gtfs.stop_times st
                        JOIN gtfs.trips t ON st.trip_id = t.trip_id
                        WHERE t.route_id = %s 
                            AND t.direction_id = %s 
                            AND st.timepoint = TRUE
                        GROUP BY stop_id
                        ORDER BY seq ASC
                    """, (route_id, direction_id))
                    ref_rows = cur.fetchall()
                reference_stops = [ReferenceStop(stop_id=row[0], stop_name=row[1], stop_sequence=row[2]) for row in ref_rows]

                # 3. Fetch Trip Data
                # Joins service_by_date to trips, then to stop_times for timepoints.
                query = """
                    SELECT 
                        st.trip_id, 
                        st.arrival_time, 
                        st.stop_id,
                        stops.stop_name,
                        st.stop_sequence
                    FROM gtfs.stop_times st
                    JOIN gtfs.trips t ON st.trip_id = t.trip_id
                    JOIN gtfs.service_by_date sbd ON t.service_id = sbd.service_id
                    JOIN gtfs.stops stops ON st.stop_id = stops.stop_id
                    WHERE sbd.date = %s
                      AND t.route_id = %s
                      AND t.direction_id = %s
                      AND st.timepoint = TRUE
                    ORDER BY st.trip_id, st.arrival_time::INTERVAL ASC;
                """
                
                cur.execute(query, (current_date_str, route_id, direction_id))
                rows = cur.fetchall()

                # 4A. Grouping & Chronological Sorting - Group stops by trip_id
                trips_map = defaultdict(list)
                for row in rows:
                    trips_map[row[0]].append({
                        "trip_id": row[0], "arrival_time": row[1],
                        "stop_id": row[2], "stop_name": row[3], "stop_sequence": row[4]
                    })

                # 4B. Define a helper to get the "absolute start time" for sorting
                # This handles the "Night Line" logic by using the interval comparison
                def get_trip_start_time(trip_stops):
                    # # Sort the stops of THIS trip by sequence to find the first one
                    # sorted_stops = sorted(trip_stops, key=lambda x: x["stop_sequence"])
                    # return sorted_stops[0]["arrival_time"]
                    return min(trip_stops, key=lambda x: x["stop_sequence"])["arrival_time"]

                sorted_trips = sorted(trips_map.values(), key=get_trip_start_time)

                final_trips = []
                for trip in sorted_trips:
                    trip.sort(key=lambda x: x["stop_sequence"])
                    for stop in trip:
                        final_trips.append(ScheduledTimetable(**stop))

                return TimetableResponse(
                    reference_stops=reference_stops, 
                    trips=final_trips
                )

                # # 4B. Define a helper to get the "absolute start time" for sorting
                # # This handles the "Night Line" logic by using the interval comparison
                # def get_trip_start_time(trip_stops):
                #     # Sort the stops of THIS trip by sequence to find the first one
                #     sorted_stops = sorted(trip_stops, key=lambda x: x["stop_sequence"])
                #     return sorted_stops[0]["arrival_time"]

                # # 5. Create a list of trips and sort them by their first appearance in the day
                # # This ensures that even if a trip starts midway, it is placed 
                # # chronologically relative to other trips' start times.
                # sorted_trips = sorted(
                #     trips_map.values(), 
                #     key=lambda t: get_trip_start_time(t)
                # )

                # # 6. Flatten the sorted trips back into a list of ScheduledStop for the response
                # # The frontend will now receive blocks of stops, where each block (trip)
                # # starts later than (or equal to) the previous block's start.
                # final_results = []
                # for trip in sorted_trips:
                #     # Sort the internal stops by sequence for table consistency
                #     trip.sort(key=lambda x: x["stop_sequence"])
                #     for stop in trip:
                #         final_results.append(ScheduledTimetable(**stop))

                # return final_results

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching schedules: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")