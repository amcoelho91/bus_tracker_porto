import json
import psycopg
from fastapi import APIRouter, HTTPException, Query
from app.config import settings

router = APIRouter()

@router.get("/shapes")
async def get_route_shape(
    route_id: str = Query(..., examples=["704"]), 
    direction_id: int = Query(..., examples=[1])
):
    query = """
        SELECT ST_AsGeoJSON(s.geom), r.route_color 
        FROM gtfs.shapes s
        LEFT JOIN gtfs.routes r ON s.route_id = r.route_id
        WHERE s.route_id = %s AND s.direction_id = %s
        LIMIT 1;
    """
    
    try:
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (route_id, direction_id))
                row = cur.fetchone()
                
                if not row:
                    return {"coordinates": [], "color": "#187EC2"}
                
                geojson = json.loads(row[0])
                # Flip [lon, lat] from PostGIS to [lat, lon] for Leaflet
                coords = [[p[1], p[0]] for p in geojson["coordinates"]]
                
                # Ensure color has the '#' prefix
                color = row[1] if row[1] else "187EC2"
                if not color.startswith("#"):
                    color = f"#{color}"
                
                return {
                    "coordinates": coords,
                    "color": color
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))