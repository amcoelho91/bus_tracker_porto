from fastapi import APIRouter, HTTPException, Path
import psycopg
import os
from pydantic import BaseModel

router = APIRouter()
DATABASE_URL = os.environ["DATABASE_URL"]

class TripHeadsignResponse(BaseModel):
    trip_id: str
    trip_headsign: str

@router.get("/trips/{trip_id}/headsign", response_model=TripHeadsignResponse)
async def get_trip_headsign(
    trip_id: str = Path(..., description="The GTFS trip_id (e.g. 12M_0_1|219|D2|T1|N9)")
):
    """
    Fetches the trip_headsign for a specific trip_id from the gtfs.trips table.
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # trip_id is a Primary Key, so this lookup is extremely fast.
                cur.execute(
                    """
                    SELECT trip_id, trip_headsign 
                    FROM gtfs.trips 
                    WHERE trip_id = %s
                    """, 
                    (trip_id,)
                )
                
                row = cur.fetchone()
                
                if not row:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Trip ID '{trip_id}' not found in GTFS schedules."
                    )
                
                return TripHeadsignResponse(
                    trip_id=row[0],
                    trip_headsign=row[1]
                )

    except HTTPException:
        raise
    except Exception as e:
        # Log the error for internal debugging
        print(f"Error fetching trip headsign: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


class TripOriginResponse(BaseModel):
    trip_id: str
    origin_stop_name: str


@router.get("/trips/{trip_id}/origin", response_model=TripOriginResponse)
async def get_trip_origin(
    trip_id: str = Path(..., description="The GTFS trip_id (e.g. 12M_0_1|219|D2|T1|N9)")
):
    """
    Fetches the stop_name of the first stop for a specific trip_id from the gtfs.stop_times and gtfs.stops tables.
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # trip_id is a Primary Key, so this lookup is extremely fast.
                cur.execute(
                    """
                    SELECT s.stop_name
                    FROM gtfs.stop_times st
                    JOIN gtfs.stops s ON st.stop_id = s.stop_id
                    WHERE st.trip_id = %s
                    AND st.stop_sequence = 1
                    """, 
                    (trip_id,)
                )
                
                row = cur.fetchone()
                
                if not row:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Trip ID '{trip_id}' not found in GTFS schedules."
                    )
                
                return TripOriginResponse(
                    trip_id=trip_id,
                    origin_stop_name=row[0]
                )

    except HTTPException:
        raise
    except Exception as e:
        # Log the error for internal debugging
        print(f"Error fetching trip origin stop name: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
