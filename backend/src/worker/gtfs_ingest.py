import os
import csv
import psycopg
from datetime import datetime

DATABASE_URL = os.environ["DATABASE_URL"]
GTFS_PATH = os.path.join(os.getcwd(), "gtfs")

def ensure_gtfs_tables():
    """Creates the static GTFS tables in the bus schema."""
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # 1. Routes Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bus.gtfs_routes (
                    route_id TEXT PRIMARY KEY,
                    route_short_name TEXT,
                    route_long_name TEXT,
                    route_color TEXT,
                    route_text_color TEXT
                );
            """)
            
            # 2. Shapes Table (with isolated ID columns)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bus.gtfs_shapes (
                    shape_id TEXT PRIMARY KEY,
                    route_id TEXT,
                    direction_id INTEGER,
                    geom geometry(LineString, 4326)
                );
            """)
            
            # Add indexes for the API queries
            cur.execute("CREATE INDEX IF NOT EXISTS idx_gtfs_shapes_route_dir ON bus.gtfs_shapes(route_id, direction_id);")
            conn.commit()

def ingest_routes():
    path = os.path.join(GTFS_PATH, "routes.txt")
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                for row in reader:
                    cur.execute("""
                        INSERT INTO bus.gtfs_routes (route_id, route_short_name, route_long_name, route_color, route_text_color)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (route_id) DO UPDATE SET
                            route_short_name = EXCLUDED.route_short_name,
                            route_long_name = EXCLUDED.route_long_name,
                            route_color = EXCLUDED.route_color,
                            route_text_color = EXCLUDED.route_text_color
                    """, (row['route_id'], row['route_short_name'], row['route_long_name'], 
                          row.get('route_color', '000000'), row.get('route_text_color', 'FFFFFF')))
                print(f"Ingested routes from {path}")

def ingest_shapes():
    path = os.path.join(GTFS_PATH, "shapes.txt")
    shape_points = {}

    print("Reading shapes.txt and parsing IDs...")
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row['shape_id']
            if sid not in shape_points:
                # Logic: 704_0_1_shp -> route_id: 704, direction_id: 0
                parts = sid.split('_')
                route_id = parts[0]
                direction_id = int(parts[1]) if len(parts) > 1 else 0
                
                shape_points[sid] = {
                    'route_id': route_id,
                    'direction_id': direction_id,
                    'pts': []
                }
            
            shape_points[sid]['pts'].append({
                'lat': float(row['shape_pt_lat']),
                'lon': float(row['shape_pt_lon']),
                'seq': int(row['shape_pt_sequence'])
            })

    print(f"Building geometries for {len(shape_points)} shapes...")
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for sid, data in shape_points.items():
                pts = data['pts']
                pts.sort(key=lambda x: x['seq'])
                
                wkt_points = ", ".join([f"{p['lon']} {p['lat']}" for p in pts])
                linestring_wkt = f"LINESTRING({wkt_points})"

                cur.execute("""
                    INSERT INTO bus.gtfs_shapes (shape_id, route_id, direction_id, geom)
                    VALUES (%s, %s, %s, ST_GeomFromText(%s, 4326))
                    ON CONFLICT (shape_id) DO UPDATE SET
                        geom = EXCLUDED.geom,
                        route_id = EXCLUDED.route_id,
                        direction_id = EXCLUDED.direction_id
                """, (sid, data['route_id'], data['direction_id'], linestring_wkt))
            conn.commit()
    print("Shapes ingestion complete.")

if __name__ == "__main__":
    print(f"--- Starting GTFS Static Ingest at {datetime.now()} ---")
    ensure_gtfs_tables()
    ingest_routes()
    ingest_shapes()
    print("--- Done ---")