SQL_LATEST_BY_ROUTE = """
SELECT
  v.fleet_vehicle_id,
  v.vehicle_id,
  v.route_id,
  v.direction,
  v.trip_id,
  v.speed,
  v.bearing,
  v.heading,
  v.observed_at,
  ST_X(v.geom) AS lon,
  ST_Y(v.geom) AS lat,
  v.last_stop_id,
  s.stop_name AS last_stop_name
FROM bus.vehicle_latest v
LEFT JOIN gtfs.stops s ON s.stop_id = v.last_stop_id
WHERE (%(route_id)s::text IS NULL OR v.route_id = %(route_id)s::text)
ORDER BY v.fleet_vehicle_id NULLS LAST;
"""

SQL_LATEST_BY_FLEET_ID = """
SELECT
  v.fleet_vehicle_id,
  v.vehicle_id,
  v.route_id,
  v.direction,
  v.trip_id,
  v.speed,
  v.bearing,
  v.heading,
  v.observed_at,
  ST_X(v.geom) AS lon,
  ST_Y(v.geom) AS lat,
  v.last_stop_id,
  s.stop_name AS last_stop_name
FROM bus.vehicle_latest v
LEFT JOIN gtfs.stops s ON s.stop_id = v.last_stop_id
WHERE fleet_vehicle_id = %(fleet_vehicle_id)s
LIMIT 1;
"""