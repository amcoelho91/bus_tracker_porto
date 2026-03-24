import os
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ["DATABASE_URL"]

SQL_MATCH_STOP = """
WITH vehicle_pos AS (
    SELECT ST_SetSRID(ST_MakePoint(%s, %s), 4326) as geom
),
route_shape AS (
    SELECT geom FROM gtfs.shapes WHERE shape_id = %s
),
distance_check AS (
    -- Calculate how far the bus is from the closest point on the line
    -- Casting to geography gives us the result in meters
    SELECT 
        ST_Distance(vp.geom::geography, rs.geom::geography) as dist_meters,
        ST_LineLocatePoint(rs.geom, vp.geom) as bus_fraction
    FROM vehicle_pos vp, route_shape rs
),
stop_positions AS (
    SELECT 
        ss.stop_id,
        s.stop_name,
        ss.stop_sequence,
        ST_LineLocatePoint(rs.geom, ST_SetSRID(ST_MakePoint(s.stop_lon, s.stop_lat), 4326)) as stop_fraction
    FROM gtfs.shape_stops ss
    JOIN gtfs.stops s ON ss.stop_id = s.stop_id
    CROSS JOIN route_shape rs
    WHERE ss.shape_id = %s
),
bus_position AS (
    SELECT ST_LineLocatePoint(rs.geom, vp.geom) as bus_fraction
    FROM vehicle_pos vp
    CROSS JOIN route_shape rs
)
SELECT 
    s.stop_id, 
    s.stop_name, 
    s.stop_sequence,
    s.stop_fraction,
    dc.bus_fraction,
    dc.dist_meters
FROM stop_positions s, distance_check dc
WHERE s.stop_fraction <= (dc.bus_fraction + 0.002)
ORDER BY s.stop_sequence DESC
LIMIT 1;
"""

def find_last_stop(lat, lon, shape_id):
    OFF_ROUTE_THRESHOLD = 150.0

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(SQL_MATCH_STOP, (lon, lat, shape_id, shape_id))
                result = cur.fetchone()
                
                if result:

                    if float(result['dist_meters']) > OFF_ROUTE_THRESHOLD:
                        print(f"\n⚠️  Warning: Bus off-route!")
                        print(f"Location might be inaccurate or bus is on a detour.")

                    else:
                        print(f"\n✅ Match Found for Shape: {shape_id}")
                        print(f"Last Stop: {result['stop_name']} ({result['stop_id']})")
                        print(f"Sequence: {result['stop_sequence']}")
                        # Using float() just in case PostGIS returns Decimal objects
                        bus_p = float(result['bus_fraction'])
                        stop_p = float(result['stop_fraction'])
                        print(f"Progress: Bus is {bus_p*100:.2f}% | Stop is {stop_p*100:.2f}%")
                else:
                    print(f"❌ No stop found behind the bus for shape {shape_id}")
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Test coordinates (Replace with real values from your map)
    test_lat = 41.1811849
    test_lon = -8.5977385
    test_shape = "704_1_1_shp" 
    
    find_last_stop(test_lat, test_lon, test_shape)