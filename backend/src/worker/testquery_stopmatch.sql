/* TEST BENCH: Geographical Logic Review
   Run this in VS Code PostgreSQL to see how each historical ping 
   matches against stops and shapes.
*/
/* TEST BENCH: Geographical Logic Review (No stop.geom version) */

-- WITH test_pings AS (
--     SELECT 
--         vehicle_id, 
--         observed_at, 
--         trip_id, 
--         geom as bus_geom
--     FROM bus.vehicle_observation
--     WHERE observed_at >= '2026-04-19'
--         --   AND trip_id = '205_0_1|223|D3|T1|N15'
--         -- AND trip_id = '508_0_1|223|D3|T1|N11'
--     --   AND trip_id = '300_0_3|223|D3|T2|N13'
--         AND trip_id = '505_0_1|223|D3|T1|N15'
-- ),
-- shape_lookup AS (
--     SELECT s.shape_id, s.geom as shape_geom
--     FROM gtfs.shapes s
--     JOIN gtfs.trips t ON s.shape_id = t.shape_id
--     -- WHERE t.trip_id = '205_0_1|223|D3|T1|N15'
--     -- WHERE t.trip_id = '508_0_1|223|D3|T1|N11'
--     -- WHERE t.trip_id = '300_0_3|223|D3|T2|N13'
--     WHERE t.trip_id = '505_0_1|223|D3|T1|N15'
--     LIMIT 1
-- ),
-- bus_stats AS (
--     SELECT 
--         tp.observed_at,
--         tp.bus_geom,
--         sl.shape_id,
--         sl.shape_geom,
--         ST_Distance(tp.bus_geom::geography, sl.shape_geom::geography) as dist_to_shape,
--         ST_LineLocatePoint(sl.shape_geom, tp.bus_geom) as bus_fraction
--     FROM test_pings tp, shape_lookup sl
-- ),
-- matched_current_stop AS (
--     -- Logic: Proximity-based match with a route-snapping guard
--     SELECT DISTINCT ON (bs.observed_at)
--         bs.observed_at,
--         ss.stop_id,
--         ss.stop_sequence,
--         ST_Distance(
--             bs.bus_geom::geography, 
--             ST_SetSRID(ST_MakePoint(s.stop_lon, s.stop_lat), 4326)::geography
--         ) as stop_dist
--     FROM bus_stats bs
--     JOIN gtfs.shape_stops ss ON ss.shape_id = bs.shape_id
--     JOIN gtfs.stops s ON ss.stop_id = s.stop_id
--     WHERE bs.dist_to_shape < 50  
--       AND ST_Distance(
--             bs.bus_geom::geography, 
--             ST_SetSRID(ST_MakePoint(s.stop_lon, s.stop_lat), 4326)::geography
--         ) < 50 
--     ORDER BY bs.observed_at, stop_dist ASC
-- ),
-- matched_last_stop AS (
--     -- Logic: Find highest sequence stop where stop_location_fraction <= bus_location_fraction
--     SELECT DISTINCT ON (bs.observed_at)
--         bs.observed_at,
--         ss.stop_id
--     FROM bus_stats bs
--     JOIN gtfs.shape_stops ss ON ss.shape_id = bs.shape_id
--     JOIN gtfs.stops s ON ss.stop_id = s.stop_id
--     WHERE 
--         -- Compare the stop's position on the line to the bus's position on the line
--         ST_LineLocatePoint(bs.shape_geom, ST_SetSRID(ST_MakePoint(s.stop_lon, s.stop_lat), 4326)) 
--         <= (bs.bus_fraction + 0.0005) -- Tiny buffer to account for GPS/Shape snapping jitter
--         AND bs.dist_to_shape < 150
--     ORDER BY bs.observed_at, ss.stop_sequence DESC
-- )
-- SELECT 
--     bs.observed_at,
--     ROUND(bs.dist_to_shape::numeric, 2) as off_route_m,
--     ROUND(bs.bus_fraction::numeric, 4) as trip_progress_pct,
--     mls.stop_id as calc_last_stop,
--     mcs.stop_id as calc_cur_stop,
--     ROUND(mcs.stop_dist::numeric, 2) as stop_proximity_m
-- FROM bus_stats bs
-- LEFT JOIN matched_last_stop mls ON bs.observed_at = mls.observed_at
-- LEFT JOIN matched_current_stop mcs ON bs.observed_at = mcs.observed_at
-- ORDER BY bs.observed_at ASC;

/* BULK REPAIR SCRIPT 
   This will update last_stop_id and cur_stop_id for all observations 
   from 2026-04-19 onwards based on the improved logic.
*/

WITH observation_set AS (
    -- Step 1: Identify all pings that need fixing
    -- We join with trips/shapes here to get the geometry context
    SELECT 
        vo.vehicle_id,
        vo.observed_at,
        t.shape_id,
        s.geom as shape_geom,
        vo.geom as bus_geom,
        ST_Distance(vo.geom::geography, s.geom::geography) as dist_to_shape,
        ST_LineLocatePoint(s.geom, vo.geom) as bus_fraction
    FROM bus.vehicle_observation vo
    JOIN gtfs.trips t ON vo.trip_id = t.trip_id
    JOIN gtfs.shapes s ON t.shape_id = s.shape_id
    -- WHERE vo.observed_at >= '2026-04-19'
),
new_logic_matches AS (
    -- Step 2: Apply the logic to find the new IDs
    SELECT 
        os.vehicle_id,
        os.observed_at,
        (
            -- Subquery for matched_current_stop
            SELECT ss.stop_id
            FROM gtfs.shape_stops ss
            JOIN gtfs.stops st ON ss.stop_id = st.stop_id
            WHERE ss.shape_id = os.shape_id
              AND os.dist_to_shape < 50
              AND ST_Distance(
                  os.bus_geom::geography, 
                  ST_SetSRID(ST_MakePoint(st.stop_lon, st.stop_lat), 4326)::geography
              ) < 50
            ORDER BY ST_Distance(os.bus_geom::geography, ST_SetSRID(ST_MakePoint(st.stop_lon, st.stop_lat), 4326)::geography) ASC
            LIMIT 1
        ) as new_cur_stop,
        (
            -- Subquery for matched_last_stop
            SELECT ss.stop_id
            FROM gtfs.shape_stops ss
            JOIN gtfs.stops st ON ss.stop_id = st.stop_id
            WHERE ss.shape_id = os.shape_id
              AND ST_LineLocatePoint(os.shape_geom, ST_SetSRID(ST_MakePoint(st.stop_lon, st.stop_lat), 4326)) 
                  <= (os.bus_fraction + 0.0005)
              AND os.dist_to_shape < 150
            ORDER BY ss.stop_sequence DESC
            LIMIT 1
        ) as new_last_stop
    FROM observation_set os
)
-- Step 3: Perform the update
UPDATE bus.vehicle_observation vo
SET 
    cur_stop_id = nlm.new_cur_stop,
    last_stop_id = COALESCE(nlm.new_cur_stop, nlm.new_last_stop)
FROM new_logic_matches nlm
WHERE vo.vehicle_id = nlm.vehicle_id 
  AND vo.observed_at = nlm.observed_at;