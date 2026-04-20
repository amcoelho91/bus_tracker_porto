-- Test Queries for GTFS and Vehicle Data

-- SELECT * FROM bus.vehicle_latest
-- WHERE route_id = '205'

SELECT COUNT(*) FROM bus.vehicle_observation;

-- SELECT * FROM bus.vehicle
-- WHERE observed_at = '2026-04-01'

SELECT * FROM bus.vehicle_observation
-- WHERE observed_at >= '2026-04-19 18:00'
WHERE observed_at >= '2026-04-20 23:31:00'
-- AND vehicle_id = '3504'
-- AND trip_id = '205_0_1|223|D3|T1|N15'
-- AND cur_stop_id IS NOT NULL
-- AND last_stop_id IS NOT NULL
-- LIMIT 60

SELECT * FROM gtfs.shapes
-- LIMIT 20
WHERE shape_id = '205_0_1|0'
-- WHERE shape_id = '300_0_3|0';

-- SELECT * FROM gtfs.shape_stops
-- WHERE shape_id = '300_0_3|0'
-- ORDER BY shape_dist_traveled ASC

SELECT * FROM gtfs.shape_stops ss
LEFT JOIN gtfs.trips t ON t.shape_id = ss.shape_id
WHERE t.trip_id = '205_0_1|223|D3|T1|N15'

-- SELECT * FROM gtfs.stops
-- WHERE stop_id = 'HSJ8';

-- SELECT * FROM gtfs.service_by_date
-- WHERE date >= '2026-03-29' AND date <= '2026-04-04'
-- ORDER BY date ASC
-- WHERE (service_id != 'ELECUTEIS'
-- AND service_id != 'ELECSAB'
-- AND service_id != 'ELECDOM')

-- SELECT 
--     service_id, 
--     COUNT(DISTINCT trip_id) AS total_trips
-- FROM 
--     gtfs.trips
-- GROUP BY 
--     service_id
-- ORDER BY 
--     total_trips DESC;

-- SELECT 
--     r.route_short_name, 
--     t.trip_headsign,
--     st.arrival_time,
--     t.service_id
-- SELECT *
-- FROM gtfs.stop_times st
-- JOIN gtfs.trips t ON st.trip_id = t.trip_id
-- -- JOIN gtfs.routes r ON t.route_id = r.route_id
-- JOIN gtfs.service_by_date sbd ON t.service_id = sbd.service_id
-- -- WHERE st.stop_id = 'BRCV' 
-- WHERE sbd.date = '2026-04-15'
-- -- AND r.route_short_name = '704'
-- AND st.arrival_time::INTERVAL >= '18:00:00'::INTERVAL 
-- AND st.arrival_time::INTERVAL <= '19:59:00'::INTERVAL
-- ORDER BY st.arrival_time::INTERVAL ASC
-- LIMIT 10;

-- SELECT direction_id, COUNT(*) 
-- FROM gtfs.shapes 
-- GROUP BY direction_id;

-- UPDATE gtfs.shapes
-- SET direction_id = CASE 
--     WHEN direction_id = 1 THEN 0
--     WHEN direction_id = 2 THEN 1
--     WHEN direction_id = 3 THEN 0
--     ELSE direction_id -- Keeps other values (like 0) unchanged
-- END
-- WHERE direction_id IN (1, 2, 3);

-- SELECT * FROM gtfs.trips
-- WHERE trip_id = '205_0_2|220|D2|T3|N9'