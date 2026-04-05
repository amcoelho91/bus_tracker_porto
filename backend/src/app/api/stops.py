import psycopg
from fastapi import APIRouter, HTTPException, Query
from app.config import settings

router = APIRouter()

@router.get("/stops")
async def get_stops_by_route(
    route_id: str = Query(..., examples=["704"]), 
    direction_id: int = Query(..., examples=[0]),
    variant_id: int = 0
):
    """
    Fetches all stops for a specific route and direction, 
    ordered by their sequence in the trip.
    """
    query = """
        SELECT 
            s.stop_id, 
            s.stop_name, 
            s.stop_lat, 
            s.stop_lon, 
            s.zone_id, 
            s.stop_url
        FROM gtfs.stops s
        JOIN gtfs.shape_stops ss ON s.stop_id = ss.stop_id
        JOIN gtfs.shapes sh ON ss.shape_id = sh.shape_id
        WHERE sh.route_id = %s AND sh.direction_id = %s AND sh.variant_id = %s
        ORDER BY ss.stop_sequence;
    """
    
    try:
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (route_id, direction_id, variant_id))
                rows = cur.fetchall()
                
                return [
                    {
                        "stop_id": row[0],
                        "stop_name": row[1],
                        "lat": row[2],
                        "lon": row[3],
                        "zone_id": row[4],
                        "stop_url": row[5]
                    } for row in rows
                ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))