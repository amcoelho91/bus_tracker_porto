SQL_LATEST_BY_ROUTE = """
SELECT
  fleet_vehicle_id,
  vehicle_id,
  route_id,
  direction,
  trip_id,
  speed,
  bearing,
  heading,
  observed_at,
  ST_X(geom) AS lon,
  ST_Y(geom) AS lat
FROM bus.vehicle_latest
WHERE (%(route_id)s::text IS NULL OR route_id = %(route_id)s::text)
ORDER BY fleet_vehicle_id NULLS LAST;
"""

SQL_LATEST_BY_FLEET_ID = """
SELECT
  fleet_vehicle_id,
  vehicle_id,
  route_id,
  direction,
  trip_id,
  speed,
  bearing,
  heading,
  observed_at,
  ST_X(geom) AS lon,
  ST_Y(geom) AS lat
FROM bus.vehicle_latest
WHERE fleet_vehicle_id = %(fleet_vehicle_id)s
LIMIT 1;
"""