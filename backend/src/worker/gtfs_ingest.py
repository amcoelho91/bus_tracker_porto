import os
import csv
import psycopg
from psycopg import sql
from datetime import datetime
import math
import re

DATABASE_URL = os.environ["DATABASE_URL"]
GTFS_PATH = os.path.join(os.getcwd(), "gtfs")
GTFS_OVERRIDE_PATH = os.path.join(GTFS_PATH, "override")  # For any manual corrections or additions to the GTFS data (e.g., missing shapes, corrected stop locations, etc.)

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
                    route_id TEXT REFERENCES gtfs.routes(route_id),
                    direction_id INTEGER,
                    variant_id INTEGER,
                    geom geometry(LineString, 4326),
                    shape_dist_traveled DOUBLE PRECISION
                );
                        
                CREATE INDEX IF NOT EXISTS idx_gtfs_shapes_geom ON gtfs.shapes USING GIST(geom);
                -- spatial index for faster geospatial queries
            """)

            # 3. Stops Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS gtfs.stops (
                    stop_id TEXT PRIMARY KEY,
                    stop_name TEXT,
                    stop_lat DOUBLE PRECISION NOT NULL,
                    stop_lon DOUBLE PRECISION NOT NULL,
                    zone_id TEXT,
                    stop_url TEXT
                );
            """)

            # 4. Trips Table
            # -- Includes two non-standard fields: shift_nr and trip_nr_in_shift 
            # -- both based on last two "fields" of trip_id's format "503_0_2|219|D3|T1|N5"
            # -- This will allow more interesting analysis
            cur.execute("""
                CREATE TABLE IF NOT EXISTS gtfs.trips (
                    trip_id TEXT PRIMARY KEY,
                    route_id TEXT REFERENCES gtfs.routes(route_id),
                    direction_id INTEGER,
                    service_id TEXT,
                    trip_headsign TEXT,
                    shape_id TEXT REFERENCES gtfs.shapes(shape_id),
                    shift_nr INTEGER, -- comes from T in trip_id
                    trip_nr_in_shift INTEGER  -- comes from N in trip_id
                );
                        
                CREATE INDEX IF NOT EXISTS idx_gtfs_trips_route_direction_service 
                    ON gtfs.trips (route_id, direction_id, service_id);
            """)

            # 5. Stop Times Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS gtfs.stop_times (
                    trip_id TEXT REFERENCES gtfs.trips(trip_id),
                    arrival_time TEXT,
                    stop_id TEXT REFERENCES gtfs.stops(stop_id),
                    stop_sequence INTEGER,
                    shape_dist_traveled DOUBLE PRECISION,
                    timepoint BOOLEAN,
                    PRIMARY KEY (trip_id, stop_sequence)
                );
                        
                CREATE INDEX IF NOT EXISTS idx_gtfs_stop_times_stop_id 
                        ON gtfs.stop_times(stop_id);
                        
                CREATE INDEX IF NOT EXISTS idx_stop_times_timepoints_only 
                        ON gtfs.stop_times (trip_id, stop_sequence) 
                        WHERE timepoint = TRUE;
            """)

            # 6. Shape-Stops Mapping (The "Bridge" table you requested)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS gtfs.shape_stops (
                    shape_id TEXT,
                    stop_id TEXT REFERENCES gtfs.stops(stop_id),
                    stop_sequence INTEGER,
                    shape_dist_traveled DOUBLE PRECISION,
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


def ingest_with_overrides(filename, sql_query, base_path=GTFS_PATH, override_path=GTFS_OVERRIDE_PATH):
    """
    Ingests a base GTFS file followed by its override counterpart.
    The sql_query MUST include an ON CONFLICT clause to handle overrides.
    """
    files_to_process = [
        os.path.join(base_path, filename),
        os.path.join(override_path, filename)
    ]

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for file_path in files_to_process:
                if not os.path.exists(file_path):
                    continue
                
                print(f"Processing {file_path}...")
                with open(file_path, mode='r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        params = {k: (v if v != '' else None) for k, v in row.items()}
                        # This assumes your query uses named placeholders like %(route_id)s
                        cur.execute(sql_query, params)
            conn.commit()


def format_gtfs_name(name: str, is_route: bool = False) -> str:
    if not name:
        return name
        
    # 1. Clean up surrounding whitespace and lowercase the entire string for easier processing
    name = name.strip().lower()
 
    # 2. Specific Route Logic: 
    if is_route:
        # Rule A: Ensure space after every dot (e.g., "st.luzia" -> "st. luzia")
        # We look for a dot followed by a non-whitespace character
        name = re.sub(r'\.(?=[^\s])', '. ', name)
        
        # Rule B: Ensure space before every "(" (e.g., "name(via)" -> "name (via)")
        name = re.sub(r'(?<=[^\s])\(', ' (', name)
        
        # Rule C: Ensure space after every ")" except at the end (e.g., "(via)name" -> "(via) name")
        # The lookahead (?=.) ensures there is at least one character following the bracket
        name = re.sub(r'\)(?=[^\s])', ') ', name)

        # Rule D: Regex replaces any hyphen (and its surrounding whitespace) with " - "
        # Only targets the separator hyphen, not hyphens inside words like -a-
        name = re.sub(r'\s*-\s*', ' - ', name)

        # Rule E: Fix the ". )" edge case -> replace with ".)"
        # We do this after the other rules to clean up any spaces we accidentally added
        name = name.replace(". )", ".)")

    # 3. Define exceptions (lower case)
    exceptions = {"da", "de", "do", "das", "dos"}
    if is_route:
        exceptions.add("via")
    
    # 4. Use regex to find "words". 
    # This matches characters after a space, a hyphen, or an opening parenthesis.
    def replace_match(match):
        word = match.group(0)
        
        # Exception: Single or double letters between hyphens (e.g., -a-, -pt-)
        # We check the context of the match
        full_string = match.string
        start, end = match.span()
        
        # Check if wrapped in hyphens
        is_between_hyphens = (start > 0 and full_string[start-1] == '-') and \
                             (end < len(full_string) and full_string[end] == '-')
        
        if word in exceptions or (is_between_hyphens and len(word) <= 2):
            return word
        
        # Otherwise, Capitalize
        return word.capitalize()

    # 4. Apply capitalization regex
    # Includes à-ú range for Portuguese characters
    formatted = re.sub(r'[a-zA-Z0-9à-úÀ-Ú]+', replace_match, name)
    
    # 5. Additional specific fixes for route names
    if is_route:
        formatted = formatted.replace(" Tic ", " TIC ")  
        formatted = formatted.replace(" Tic)", " TIC)")
        formatted = formatted.replace("(Tic)", "(TIC)")
        formatted = formatted.replace("(Est)", "(Est.)")

    # 6. Final Cleanup
    # Remove any double spaces that might have been created by the dot-space rule
    return re.sub(r'\s+', ' ', formatted).strip()

# Helper aliases for clarity in your ingestion scripts
def format_stop_name(name: str) -> str:
    return format_gtfs_name(name, is_route=False)

def format_route_name(name: str) -> str:
    return format_gtfs_name(name, is_route=True)


def ingest_routes():
    print("Ingesting routes with potential overrides...")
    sql = """
        INSERT INTO gtfs.routes (route_id, route_short_name, route_long_name, route_color, route_text_color)
        VALUES (%(route_id)s, %(route_short_name)s, %(route_long_name)s, %(route_color)s, %(route_text_color)s)
        ON CONFLICT (route_id) DO UPDATE SET
            route_short_name = EXCLUDED.route_short_name,
            route_long_name = EXCLUDED.route_long_name,
            route_color = EXCLUDED.route_color,
            route_text_color = EXCLUDED.route_text_color;
    """
    ingest_with_overrides("routes.txt", sql)
    update_route_name_case()


def process_shapes_file(file_path, cur):
    """Internal helper to process a specific shapes.txt file."""
    if not os.path.exists(file_path):
        return

    print(f"Processing shapes from {file_path}...")
    shapes = {}
    with open(file_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            shape_id = row['shape_id']
            if shape_id not in shapes:
                parts = shape_id.split('_')
                route_id = parts[0]
                shape_direction_raw_id = int(parts[2].split('|')[0]) if len(parts) > 1 else 0
                # shape_direction_raw_id override:
                # 1 -> 0 (Inbound/Ida), 2 -> 1 (Outbound/Volta), 3 -> 0 (Circular), anything else defaults to 0
                direction_id = 1 if shape_direction_raw_id == 2 else 0  
                variant_id = int(parts[2].split('|')[1]) if len(parts) > 1 else 0
                
                shapes[shape_id] = {
                    'route_id': route_id,
                    'direction_id': direction_id,
                    'variant_id': variant_id,
                    'pts': [],
                    'shape_dist_traveled': 0.0
                }
            
            shapes[shape_id]['pts'].append({
                'lat': float(row['shape_pt_lat']),
                'lon': float(row['shape_pt_lon']),
                'seq': int(row['shape_pt_sequence']),
                'shape_dist_traveled': float(row['shape_dist_traveled']) if row['shape_dist_traveled'] else 0.0
            })

    print(f"Building geometries for {len(shapes)} shapes from {os.path.basename(file_path)}...")
    for shape_id, data in shapes.items():
        pts = data['pts']
        pts.sort(key=lambda x: x['seq'])
        
        wkt_points = ", ".join([f"{p['lon']} {p['lat']}" for p in pts])
        linestring_wkt = f"LINESTRING({wkt_points})"

        # UPSERT logic: If shape_id exists (from base), replace the geom (from override)
        cur.execute("""
            INSERT INTO gtfs.shapes (shape_id, route_id, direction_id, variant_id, geom, shape_dist_traveled)
            VALUES (%s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s)
            ON CONFLICT (shape_id) DO UPDATE SET
                geom = EXCLUDED.geom,
                route_id = EXCLUDED.route_id,
                direction_id = EXCLUDED.direction_id,
                variant_id = EXCLUDED.variant_id,
                shape_dist_traveled = EXCLUDED.shape_dist_traveled;
        """, (shape_id, data['route_id'], data['direction_id'], data['variant_id'], linestring_wkt, data['shape_dist_traveled']))


def ingest_shapes():
    print("Ingesting shapes with potential overrides...")
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # 1. Process Base Files
            base_file = os.path.join(GTFS_PATH, "shapes.txt")
            process_shapes_file(base_file, cur)

            # 2. Process Override Files
            override_file = os.path.join(GTFS_OVERRIDE_PATH, "shapes.txt")
            process_shapes_file(override_file, cur)
            
            conn.commit()
    print("Shapes ingestion complete.")


def update_stop_name_case():
    print("Formatting stop name cases...")
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # 1. Fetch all stops
                cur.execute("SELECT stop_id, stop_name FROM gtfs.stops")
                rows = cur.fetchall()
                
                # 2. Prepare the update data
                update_data = []
                for stop_id, original_name in rows:
                    formatted_name = format_stop_name(original_name)
                    if formatted_name != original_name:
                        update_data.append((formatted_name, stop_id))

                # 3. Batch Update
                if update_data:
                    cur.executemany(
                        "UPDATE gtfs.stops SET stop_name = %s WHERE stop_id = %s",
                        update_data
                    )
                    conn.commit()
                    print(f"Success! Updated {len(update_data)} stop names.")
                else:
                    print("No changes needed. All stops already match the format.")
                    
    except Exception as e:
        print(f"Error updating database: {e}")

def update_route_name_case():
    print("Formatting route name cases...")
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # 1. Fetch all routes
                cur.execute("SELECT route_id, route_long_name FROM gtfs.routes")
                rows = cur.fetchall()
                
                # 2. Prepare the update data
                update_data = []
                for route_id, original_name in rows:
                    formatted_name = format_route_name(original_name)
                    if formatted_name != original_name:
                        update_data.append((formatted_name, route_id))

                # 3. Batch Update
                if update_data:
                    cur.executemany(
                        "UPDATE gtfs.routes SET route_long_name = %s WHERE route_id = %s",
                        update_data
                    )
                    conn.commit()
                    print(f"Success! Updated {len(update_data)} route names.")
                else:
                    print("No changes needed. All routes already match the format.")

    except Exception as e:
        print(f"Error updating database: {e}")


def ingest_stops():
    print("Ingesting stops with potential overrides...")

    sql = """
        INSERT INTO gtfs.stops (stop_id, stop_name, stop_lat, stop_lon, zone_id, stop_url)
        VALUES (%(stop_id)s, %(stop_name)s, %(stop_lat)s, %(stop_lon)s, %(zone_id)s, %(stop_url)s)
        ON CONFLICT (stop_id) DO UPDATE SET
            stop_name = EXCLUDED.stop_name;
    """
    # Note: we use the dictionary directly from DictReader via the helper
    ingest_with_overrides("stops.txt", sql)
    print("Stops ingested.")

    update_stop_name_case()


def ingest_trips():
    print("Ingesting trips with potential overrides...")
    sql = """
        INSERT INTO gtfs.trips (trip_id, route_id, direction_id, service_id, trip_headsign, shape_id)
        VALUES (%(trip_id)s, %(route_id)s, %(direction_id)s, %(service_id)s, %(trip_headsign)s, %(shape_id)s)
        ON CONFLICT (trip_id) DO NOTHING;
    """
    ingest_with_overrides("trips.txt", sql)
    print("Trips ingested. Now updating shift_nr and trip_nr_in_shift based on trip_id format...")

    # The trips table includes two non-standard fields: shift_nr and trip_nr_in_shift 
    # -- both based on last two "fields" of trip_id's format "503_0_2|219|D3|T1|N5"
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE gtfs.trips
                SET 
                    shift_nr = CAST(SUBSTRING(SPLIT_PART(trip_id, '|', 4) FROM 2) AS INTEGER),
                    trip_nr_in_shift = CAST(SUBSTRING(SPLIT_PART(trip_id, '|', 5) FROM 2) AS INTEGER)
                WHERE trip_id LIKE '%|T%|N%';
            """)
            conn.commit()

    print("Shift and trip numbers updated.")


def ingest_stop_times():
    print("Ingesting stop_times with potential overrides (this might take a while)...")
    sql = """
        INSERT INTO gtfs.stop_times (trip_id, stop_id, stop_sequence, arrival_time, timepoint, shape_dist_traveled)
        VALUES (%(trip_id)s, %(stop_id)s, %(stop_sequence)s, %(arrival_time)s, %(timepoint)s, %(shape_dist_traveled)s)
        ON CONFLICT DO NOTHING;
    """
    ingest_with_overrides("stop_times.txt", sql)
    print("Stop times ingested.")


def get_shapes_without_shape_dist_traveled(cur):
    # Get the maximum shape_dist_traveled of each individual shape 
    cur.execute("""
        SELECT shape_id, MAX(shape_dist_traveled) as max_dist
        FROM gtfs.shape_stops
        GROUP BY shape_id;
    """)
    # Filter the shapes for which the maximum shape_dist_traveled is 0 or NULL
    shapes_without_dist = [row[0] for row in cur.fetchall() if row[1] is None or row[1] == 0.0]
    if shapes_without_dist:
        print(f"Shapes without shape_dist_traveled calculated: {shapes_without_dist}")
        return shapes_without_dist
    else:
        print("All shapes have shape_dist_traveled calculated.")
        return []
    

def associate_stops_to_shapes():
    print("Building shape-to-stop associations using the longest available trips...")
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # 1. Clear the table to ensure we don't keep partial route data
            cur.execute("TRUNCATE gtfs.shape_stops;")

            # for every unique shape_id in trips, using one trip_id (that uses the shape_id),
            # find the stops in stop_times, insert into shape_stops
            # (with the shape_id from trips and the stop_sequence and shape_dist_traveled from stop_times)

            cur.execute("""
                INSERT INTO gtfs.shape_stops (shape_id, stop_id, stop_sequence, shape_dist_traveled)
                SELECT DISTINCT ON (t.shape_id, st.stop_sequence)
                    t.shape_id,
                    st.stop_id,
                    st.stop_sequence,
                    st.shape_dist_traveled
                FROM gtfs.trips t
                JOIN gtfs.stop_times st ON t.trip_id = st.trip_id
                WHERE t.shape_id IS NOT NULL
                ORDER BY t.shape_id, st.stop_sequence, t.trip_id
                ON CONFLICT DO NOTHING;
            """)

            # if shape_dist_traveled is missing, calculate it now based on the geometries and stop locations
            if not get_shapes_without_shape_dist_traveled(cur):
                calculate_cumulative_shape_distances(cur)
            
            conn.commit()
    print("Shape-to-stop associations built successfully.")

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points in meters."""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlambda = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

def calculate_cumulative_shape_distances(cur, shapes_to_process=[]):
    print("Calculating shape_dist_traveled for the folloing shapes...")
    print(shapes_to_process if shapes_to_process else "All shapes")

    if not shapes_to_process:
        # If no specific shapes were provided, we calculate for all shapes
        cur.execute("SELECT DISTINCT shape_id FROM gtfs.shape_stops;")
        shapes_to_process = [row[0] for row in cur.fetchall()]

    # 1. Get all shapes and their points in order
    # Note: If your geom is a LineString, it's easier to pull points via PostGIS functions
    cur.execute("""
        SELECT 
            shape_id, 
            (dp).path[1] as pt_seq,
            ST_X((dp).geom) as lon,
            ST_Y((dp).geom) as lat
        FROM (
            SELECT shape_id, ST_DumpPoints(geom) as dp 
            FROM gtfs.shapes
        ) AS dumped
        ORDER BY shape_id, pt_seq
    """)
    
    from collections import defaultdict
    shape_data = defaultdict(list)
    for shape_id, seq, lon, lat in cur.fetchall():
        shape_data[shape_id].append({'lat': lat, 'lon': lon, 'dist': 0.0})

    # 2. Pre-calculate cumulative distance along each shape
    for shape_id, pts in shape_data.items():
        total_dist = 0.0
        for i in range(1, len(pts)):
            p1, p2 = pts[i-1], pts[i]
            # Haversine or use PostGIS ST_Distance(geog, geog) for accuracy
            dist = haversine_distance(p1['lat'], p1['lon'], p2['lat'], p2['lon'])
            total_dist += dist
            pts[i]['dist'] = total_dist

    # 3. Fetch stops associated with these shapes
    cur.execute("""
        SELECT ss.shape_id, ss.stop_id, ss.stop_sequence, s.stop_lat, s.stop_lon
        FROM gtfs.shape_stops ss
        JOIN gtfs.stops s ON ss.stop_id = s.stop_id
        ORDER BY ss.shape_id, ss.stop_sequence ASC
    """)
    
    # Keep track of the current shape to handle the "list reduction" per route
    current_shape_id = None
    pts = []

    # 4. Map stops to the nearest cumulative distance on the shape
    # We use a cursor.fetchall() or a separate list to avoid iterator conflicts
    stops_to_process = cur.fetchall() 

    for shape_id, stop_id, stop_seq, s_lat, s_lon in stops_to_process:
        # Reset the points list only when we switch to a new shape
        if shape_id != current_shape_id:
            current_shape_id = shape_id
            # Get a fresh copy of the points for this specific shape
            pts = list(shape_data.get(shape_id, []))
            
        if not pts:
            continue
        
        # Find the index of the closest point in the remaining list
        # enumerate allows us to find the position so we can slice correctly
        best_idx, best_pt = min(
            enumerate(pts), 
            key=lambda x: haversine_distance(s_lat, s_lon, x[1]['lat'], x[1]['lon'])
        )
        
        # Update the database using the absolute distance pre-calculated in Step 2
        cur.execute("""
            UPDATE gtfs.shape_stops 
            SET shape_dist_traveled = %s 
            WHERE shape_id = %s AND stop_sequence = %s
        """, (best_pt['dist'], shape_id, stop_seq))

        # Slice the list. All points before this stop are now "in the past" and removed from the search
        pts = pts[best_idx:]


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


def generate_service_calendar(with_calendar_txt=True):
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

            if with_calendar_txt:
                print("(with calendar.txt) Populating service_by_date by combining calendar and calendar_dates...")
                # 2A. Populate it by combining calendar and calendar_dates logic
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

            else:
                print("(without calendar.txt) Populating service_by_date directly from calendar_dates...")
                # 2B. If calendar.txt is missing, we can still populate the lookup with calendar_dates only
                cur.execute("""
                    INSERT INTO gtfs.service_by_date (date, service_id)
                    SELECT TO_DATE(date, 'YYYYMMDD'), service_id
                    FROM gtfs.calendar_dates
                    WHERE exception_type = 1;
                """)

            conn.commit()
    print("Service lookup table generated successfully.")

def remove_shape_dist_traveled_from_shapes_and_stop_times():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE gtfs.shapes DROP COLUMN IF EXISTS shape_dist_traveled;")
            cur.execute("ALTER TABLE gtfs.stop_times DROP COLUMN IF EXISTS shape_dist_traveled;")
            conn.commit()
    print("Removed shape_dist_traveled from shapes and stop_times tables.")

def is_gtfs_loaded(cur):
    """Check if the schema exists and has data."""
    # 1. Check if the table exists in the database catalog
    cur.execute("""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_schema = 'gtfs' 
            AND table_name = 'shape_stops'
        );
    """)
    if not cur.fetchone()[0]:
        return False

    # 2. If it exists, check if it actually has data
    cur.execute("SELECT EXISTS (SELECT 1 FROM gtfs.shape_stops LIMIT 1);")
    return cur.fetchone()[0]

def delete_gtfs_tables():
    # If a new GTFS file was downloaded and processed, 
    # we need to empty the existing GTFS tables before re-ingesting the new data.
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA IF EXISTS gtfs CASCADE;")
            cur.execute("CREATE SCHEMA gtfs;")
            print("GTFS tables cleared (schema dropped and recreated).")


def main():
    # Run gtfs_update.py first to check for new files and download if needed
    from .gtfs_update import main as gtfs_update_main
    if gtfs_update_main():
        delete_gtfs_tables()  # Clear existing data before re-ingestion
    else:
        print("\n\nChecking if GTFS ingestion is needed...")

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            if not is_gtfs_loaded(cur):
                print("GTFS Database empty. Running full ingestion...")
                print(f"--- Starting GTFS Static Ingest at {datetime.now()} ---")
                ensure_gtfs_tables()
                ingest_routes()
                ingest_shapes()
                ingest_stops()
                ingest_trips()
                ingest_stop_times()

                if os.path.exists(os.path.join(GTFS_PATH, "calendar.txt")):
                    ingest_calendar()
                    ingest_calendar_dates()
                    generate_service_calendar(with_calendar_txt=True)
                else:
                    ingest_calendar_dates()
                    generate_service_calendar(with_calendar_txt=False)

                associate_stops_to_shapes()

                # remove unnecesary info:
                # 1. shape_dist_traveled in shapes and in stop_times (we keep it only in shape_stops)
                remove_shape_dist_traveled_from_shapes_and_stop_times()
                # 2. simplify shapes? maybe remove points that are too close to each other? 

                print("--- Done ---")
            else:
                print("GTFS database detected!")

if __name__ == "__main__":
    main()