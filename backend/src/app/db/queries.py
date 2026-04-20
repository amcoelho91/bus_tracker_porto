SQL_LATEST_BY_ROUTE = """
SELECT
  v.vehicle_id,
  v.route_id,
  v.direction,
  v.trip_id,
  v.heading,
  v.observed_at,
  ST_X(v.geom) AS lon,
  ST_Y(v.geom) AS lat,
  v.last_stop_id,
  v.cur_stop_id,
  s.stop_name AS last_stop_name,
  r.route_long_name,
  t.trip_headsign
FROM bus.vehicle_latest v
LEFT JOIN gtfs.stops s ON s.stop_id = v.last_stop_id
LEFT JOIN gtfs.routes r ON r.route_id = v.route_id
LEFT JOIN gtfs.trips t ON v.trip_id = t.trip_id
WHERE (%(route_id)s::text IS NULL OR v.route_id = %(route_id)s::text)
ORDER BY v.fleet_vehicle_id NULLS LAST;
"""

SQL_LATEST_BY_FLEET_ID = """
SELECT
  v.vehicle_id,
  v.route_id,
  v.direction,
  v.trip_id,
  v.heading,
  v.observed_at,
  ST_X(v.geom) AS lon,
  ST_Y(v.geom) AS lat,
  v.cur_stop_id,
  v.last_stop_id,
  s.stop_name AS last_stop_name,
  r.route_long_name,
  t.trip_headsign
FROM bus.vehicle_latest v
LEFT JOIN gtfs.stops s ON s.stop_id = v.last_stop_id
LEFT JOIN gtfs.routes r ON r.route_id = v.route_id
LEFT JOIN gtfs.trips t ON v.trip_id = t.trip_id
WHERE v.vehicle_id = %(fleet_vehicle_id)s
LIMIT 1;
"""