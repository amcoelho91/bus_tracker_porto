import psycopg
from fastapi import APIRouter, HTTPException
from app.config import settings

router = APIRouter()

@router.get("/routes")
async def get_all_routes():
    """Fetches all available routes for the selection list."""
    query = """
        SELECT route_id, route_short_name, route_long_name 
        FROM gtfs.routes 
        ORDER BY 
            CASE 
                WHEN route_id ~ '^[0-9]+$' THEN route_id::integer 
                ELSE 9999 
            END, 
            route_id;
    """
    
    try:
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                
                return [
                    {
                        "route_id": row[0],
                        "route_short_name": row[1],
                        "route_long_name": row[2]
                    } for row in rows
                ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))