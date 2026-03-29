SELECT * FROM bus.vehicle_observation
WHERE observed_at >= '2026-03-29 20:00:00'
-- AND cur_stop_id IS NOT NULL
-- AND last_stop_id IS NOT NULL
-- WHERE (observed_at >= '2026-03-29'
-- AND route_id = '300')

-- SELECT * FROM gtfs.shape_stops
-- WHERE shape_id = '300_0_1_shp'
-- ORDER BY shape_dist_traveled ASC