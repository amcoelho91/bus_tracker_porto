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
            cur.execute("CREATE SCHEMA IF NOT EXISTS gtfs;")
            
            # 1. Routes Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS gtfs.routes (
                    route_id TEXT PRIMARY KEY,
                    route_short_name TEXT,
                    route_long_name TEXT,
                    route_color TEXT,
                    route_text_color TEXT
                );
            """)
            
            # 2. Shapes Table (with isolated ID columns)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS gtfs.shapes (
                    shape_id TEXT PRIMARY KEY,
                    route_id TEXT,
                    direction_id INTEGER,
                    geom geometry(LineString, 4326)
                );
            """)

            # 3. Stops Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS gtfs.stops (
                    stop_id TEXT PRIMARY KEY,
                    stop_name TEXT,
                    stop_lat DOUBLE PRECISION,
                    stop_lon DOUBLE PRECISION,
                    zone_id TEXT,
                    stop_url TEXT
                );
            """)

            # 4. Trips Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS gtfs.trips (
                    trip_id TEXT PRIMARY KEY,
                    route_id TEXT,
                    direction_id INTEGER,
                    service_id TEXT,
                    trip_headsign TEXT,
                    shape_id TEXT
                );
            """)

            # 5. Stop Times Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS gtfs.stop_times (
                    trip_id TEXT REFERENCES gtfs.trips(trip_id),
                    arrival_time TEXT,
                    departure_time TEXT,
                    stop_id TEXT REFERENCES gtfs.stops(stop_id),
                    stop_sequence INTEGER,
                    PRIMARY KEY (trip_id, stop_sequence)
                );
            """)

            # 6. Shape-Stops Mapping (The "Bridge" table you requested)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS gtfs.shape_stops (
                    shape_id TEXT,
                    stop_id TEXT REFERENCES gtfs.stops(stop_id),
                    stop_sequence INTEGER,
                    PRIMARY KEY (shape_id, stop_sequence)
                );
            """)
            
            # Add indexes for the API queries
            cur.execute("CREATE INDEX IF NOT EXISTS idx_gtfs_shapes_route_dir ON gtfs.shapes(route_id, direction_id);")
            conn.commit()

def ingest_routes():
    path = os.path.join(GTFS_PATH, "routes.txt")
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                for row in reader:
                    cur.execute("""
                        INSERT INTO gtfs.routes (route_id, route_short_name, route_long_name, route_color, route_text_color)
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
                    INSERT INTO gtfs.shapes (shape_id, route_id, direction_id, geom)
                    VALUES (%s, %s, %s, ST_GeomFromText(%s, 4326))
                    ON CONFLICT (shape_id) DO UPDATE SET
                        geom = EXCLUDED.geom,
                        route_id = EXCLUDED.route_id,
                        direction_id = EXCLUDED.direction_id
                """, (sid, data['route_id'], data['direction_id'], linestring_wkt))
            conn.commit()
    print("Shapes ingestion complete.")

def ingest_stops():
    path = os.path.join(GTFS_PATH, "stops.txt")
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                for row in reader:
                    cur.execute("""
                        INSERT INTO gtfs.stops (stop_id, stop_name, stop_lat, stop_lon, zone_id, stop_url)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (stop_id) DO UPDATE SET
                            stop_name = EXCLUDED.stop_name
                    """, (row['stop_id'], row['stop_name'], row['stop_lat'], row['stop_lon'], 
                          row.get('zone_id'), row.get('stop_url')))
                conn.commit()
    print("Stops ingested.")

def ingest_trips():
    path = os.path.join(GTFS_PATH, "trips.txt")
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                for row in reader:
                    cur.execute("""
                        INSERT INTO gtfs.trips (trip_id, route_id, direction_id, service_id, trip_headsign, shape_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (trip_id) DO NOTHING
                    """, (row['trip_id'], row['route_id'], row['direction_id'], row['service_id'], 
                          row.get('trip_headsign'), row['shape_id']))
                conn.commit()
    print("Trips ingested.")

def ingest_stop_times():
    path = os.path.join(GTFS_PATH, "stop_times.txt")
    print("Ingesting stop_times (this might take a while)...")
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Using a batch approach here because stop_times is usually HUGE
                # But for simplicity, following your existing pattern:
                for row in reader:
                    cur.execute("""
                        INSERT INTO gtfs.stop_times (trip_id, stop_id, stop_sequence, arrival_time, departure_time)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (row['trip_id'], row['stop_id'], row['stop_sequence'], 
                          row['arrival_time'], row['departure_time']))
                conn.commit()
    print("Stop times ingested.")

def associate_stops_to_shapes():
    print("Building shape-to-stop associations...")
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO gtfs.shape_stops (shape_id, stop_id, stop_sequence)
                SELECT DISTINCT ON (t.shape_id, st.stop_sequence)
                    t.shape_id,
                    st.stop_id,
                    st.stop_sequence
                FROM gtfs.trips t
                JOIN gtfs.stop_times st ON t.trip_id = st.trip_id
                WHERE t.shape_id IS NOT NULL
                ORDER BY t.shape_id, st.stop_sequence, t.trip_id
                ON CONFLICT DO NOTHING;
            """)
            conn.commit()
    print("Associations complete.")

if __name__ == "__main__":
    print(f"--- Starting GTFS Static Ingest at {datetime.now()} ---")
    ensure_gtfs_tables()
    ingest_routes()
    ingest_shapes()
    ingest_stops()
    ingest_trips()
    ingest_stop_times()
    associate_stops_to_shapes()
    print("--- Done ---")