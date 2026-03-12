from app.db.session import get_conn

SQL_LATEST_WITH_PREV_BASE = """
SELECT
  l.fleet_vehicle_id,
  l.vehicle_id,
  l.route_id,
  l.direction,
  l.trip_id,
  l.speed,
  l.bearing,
  l.heading,
  l.observed_at,
  ST_X(l.geom) AS lon,
  ST_Y(l.geom) AS lat,

  p.prev_observed_at,
  p.prev_lon,
  p.prev_lat
FROM bus.vehicle_latest l
LEFT JOIN LATERAL (
  SELECT
    o.observed_at AS prev_observed_at,
    ST_X(o.geom) AS prev_lon,
    ST_Y(o.geom) AS prev_lat
  FROM bus.vehicle_observation o
  WHERE o.vehicle_id = l.vehicle_id
    AND o.observed_at < l.observed_at
  ORDER BY o.observed_at DESC
  LIMIT 1
) p ON TRUE
"""

SQL_ORDER = " ORDER BY l.fleet_vehicle_id NULLS LAST;"

def get_latest_by_route_and_direction(route_id: str | None, direction: int | None):
    route_id = route_id.strip() if route_id else None
    filters = []
    params: dict = {}

    # pedropt10: Only show buses that reported in the last 20 minutes
    filters.append("l.observed_at > NOW() - INTERVAL '20 minutes'")

    if route_id:
        filters.append("l.route_id = %(route_id)s")
        params["route_id"] = route_id

    if direction is not None:
        filters.append("l.direction = %(direction)s")
        params["direction"] = direction

    where = ""
    if filters:
        where = " WHERE " + " AND ".join(filters)

    sql = SQL_LATEST_WITH_PREV_BASE + where + SQL_ORDER

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

def get_latest_by_fleet_id(fleet_vehicle_id: str):
    sql = SQL_LATEST_WITH_PREV_BASE + " WHERE l.fleet_vehicle_id = %(fleet_vehicle_id)s LIMIT 1;"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"fleet_vehicle_id": fleet_vehicle_id})
            return cur.fetchone()