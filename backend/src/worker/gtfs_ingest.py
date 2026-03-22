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

            # 7. Calendar Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS gtfs.calendar (
                    service_id TEXT PRIMARY KEY,
                    monday INTEGER,
                    tuesday INTEGER,
                    wednesday INTEGER,
                    thursday INTEGER,
                    friday INTEGER,
                    saturday INTEGER,
                    sunday INTEGER,
                    start_date TEXT,
                    end_date TEXT
                );
            """)

            # 8. Calendar Dates Table (Exceptions)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS gtfs.calendar_dates (
                    service_id TEXT,
                    date TEXT,
                    exception_type INTEGER,
                    PRIMARY KEY (service_id, date)
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
    print("Building shape-to-stop associations using the longest available trips...")
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # 1. Clear the table to ensure we don't keep partial route data
            cur.execute("TRUNCATE gtfs.shape_stops;")
            
            # 2. Insert the stops from the trip that reaches the highest sequence number
            cur.execute("""
                INSERT INTO gtfs.shape_stops (shape_id, stop_id, stop_sequence)
                WITH TripMaxSequence AS (
                    -- Find the maximum sequence reached by each trip
                    SELECT 
                        t.shape_id, 
                        t.trip_id, 
                        MAX(st.stop_sequence) as final_sequence
                    FROM gtfs.trips t
                    JOIN gtfs.stop_times st ON t.trip_id = st.trip_id
                    WHERE t.shape_id IS NOT NULL
                    GROUP BY t.shape_id, t.trip_id
                ),
                LongestTrips AS (
                    -- For each shape, pick the trip_id that has the absolute highest sequence
                    SELECT DISTINCT ON (shape_id)
                        shape_id,
                        trip_id
                    FROM TripMaxSequence
                    ORDER BY shape_id, final_sequence DESC
                )
                -- Map the stops from that specific "Master Trip" to the shape
                SELECT 
                    lt.shape_id,
                    st.stop_id,
                    st.stop_sequence
                FROM LongestTrips lt
                JOIN gtfs.stop_times st ON lt.trip_id = st.trip_id
                ON CONFLICT DO NOTHING;
            """)
            conn.commit()
    print("Shape-to-stop associations built successfully.")
    # print("Building shape-to-stop associations...")
    # with psycopg.connect(DATABASE_URL) as conn:
    #     with conn.cursor() as cur:
    #         cur.execute("""
    #             INSERT INTO gtfs.shape_stops (shape_id, stop_id, stop_sequence)
    #             SELECT DISTINCT ON (t.shape_id, st.stop_sequence)
    #                 t.shape_id,
    #                 st.stop_id,
    #                 st.stop_sequence
    #             FROM gtfs.trips t
    #             JOIN gtfs.stop_times st ON t.trip_id = st.trip_id
    #             WHERE t.shape_id IS NOT NULL
    #             ORDER BY t.shape_id, st.stop_sequence, t.trip_id
    #             ON CONFLICT DO NOTHING;
    #         """)
    #         conn.commit()
    # print("Associations complete.")

def ingest_calendar():
    path = os.path.join(GTFS_PATH, "calendar.txt")
    print("Ingesting calendar.txt...")
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                for row in reader:
                    cur.execute("""
                        INSERT INTO gtfs.calendar (
                            service_id, monday, tuesday, wednesday, thursday, 
                            friday, saturday, sunday, start_date, end_date
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (service_id) DO UPDATE SET
                            monday = EXCLUDED.monday, tuesday = EXCLUDED.tuesday,
                            wednesday = EXCLUDED.wednesday, thursday = EXCLUDED.thursday,
                            friday = EXCLUDED.friday, saturday = EXCLUDED.saturday,
                            sunday = EXCLUDED.sunday, start_date = EXCLUDED.start_date,
                            end_date = EXCLUDED.end_date
                    """, (row['service_id'], row['monday'], row['tuesday'], row['wednesday'], 
                          row['thursday'], row['friday'], row['saturday'], row['sunday'], 
                          row['start_date'], row['end_date']))
                conn.commit()

def ingest_calendar_dates():
    path = os.path.join(GTFS_PATH, "calendar_dates.txt")
    print("Ingesting calendar_dates.txt...")
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                for row in reader:
                    cur.execute("""
                        INSERT INTO gtfs.calendar_dates (service_id, date, exception_type)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (service_id, date) DO UPDATE SET
                            exception_type = EXCLUDED.exception_type
                    """, (row['service_id'], row['date'], row['exception_type']))
                conn.commit()

def generate_service_calendar():
    print("Generating the active service lookup table (service_by_date)...")
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # 1. Create the lookup table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS gtfs.service_by_date (
                    date DATE,
                    service_id TEXT,
                    PRIMARY KEY (date, service_id)
                );
                TRUNCATE gtfs.service_by_date;
            """)

            # 2. Populate it by combining calendar and calendar_dates logic
            cur.execute("""
                INSERT INTO gtfs.service_by_date (date, service_id)
                SELECT d.date, c.service_id
                FROM (
                    -- Generate all dates for 2026
                    SELECT generate_series(
                        '2026-01-01'::date, 
                        '2026-12-31'::date, 
                        '1 day'::interval
                    )::date AS date
                ) d
                JOIN gtfs.calendar c ON 
                    d.date >= TO_DATE(c.start_date, 'YYYYMMDD') AND 
                    d.date <= TO_DATE(c.end_date, 'YYYYMMDD') AND (
                        (EXTRACT(DOW FROM d.date) = 1 AND c.monday = 1) OR
                        (EXTRACT(DOW FROM d.date) = 2 AND c.tuesday = 1) OR
                        (EXTRACT(DOW FROM d.date) = 3 AND c.wednesday = 1) OR
                        (EXTRACT(DOW FROM d.date) = 4 AND c.thursday = 1) OR
                        (EXTRACT(DOW FROM d.date) = 5 AND c.friday = 1) OR
                        (EXTRACT(DOW FROM d.date) = 6 AND c.saturday = 1) OR
                        (EXTRACT(DOW FROM d.date) = 0 AND c.sunday = 1)
                    )
                -- Remove services that have an exception_type 2 (removed) for that date
                WHERE NOT EXISTS (
                    SELECT 1 FROM gtfs.calendar_dates cd 
                    WHERE cd.service_id = c.service_id 
                      AND cd.date = TO_CHAR(d.date, 'YYYYMMDD') 
                      AND cd.exception_type = 2
                )
                UNION
                -- Add services that have an exception_type 1 (added) for that date
                SELECT TO_DATE(cd.date, 'YYYYMMDD'), cd.service_id
                FROM gtfs.calendar_dates cd
                WHERE cd.exception_type = 1;
            """)
            conn.commit()
    print("Service lookup table generated successfully.")

if __name__ == "__main__":
    print(f"--- Starting GTFS Static Ingest at {datetime.now()} ---")
    ensure_gtfs_tables()
    ingest_routes()
    ingest_shapes()
    ingest_stops()
    ingest_trips()
    ingest_stop_times()
    ingest_calendar()
    ingest_calendar_dates()
    generate_service_calendar()
    associate_stops_to_shapes()
    print("--- Done ---")