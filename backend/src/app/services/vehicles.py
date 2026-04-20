from app.db.session import get_conn

SQL_LATEST_WITH_PREV_BASE = """
SELECT
  l.vehicle_id,
  l.route_id,
  l.direction,
  l.trip_id,
  l.heading,
  l.observed_at,
  l.last_stop_id,
  l.cur_stop_id,
  ST_X(l.geom) AS lon,
  ST_Y(l.geom) AS lat,
  s.stop_name AS last_stop_name,
  r.route_long_name,
  t.trip_headsign,
  p.prev_observed_at,
  p.prev_lon,
  p.prev_lat,
  p.prev_heading
FROM bus.vehicle_latest l
LEFT JOIN gtfs.stops s ON l.last_stop_id = s.stop_id
LEFT JOIN gtfs.routes r ON l.route_id = r.route_id
LEFT JOIN gtfs.trips t ON l.trip_id = t.trip_id
LEFT JOIN LATERAL (
  SELECT
    o.observed_at AS prev_observed_at,
    ST_X(o.geom) AS prev_lon,
    ST_Y(o.geom) AS prev_lat,
    o.heading AS prev_heading
  FROM bus.vehicle_observation o
  WHERE o.vehicle_id = l.vehicle_id
    AND o.observed_at < l.observed_at
  ORDER BY o.observed_at DESC
  LIMIT 1
) p ON TRUE
"""

SQL_ORDER = " ORDER BY l.vehicle_id NULLS LAST;"

def get_latest_by_route_and_direction(route_id: str | None, direction: int | None):
    route_id = route_id.strip() if route_id else None
    filters = []
    params: dict = {}

    # Only show buses that reported in the last 20 minutes
    filters.append("l.observed_at > NOW() - INTERVAL '20 minutes'")
    # filters.append("l.observed_at > NOW() - INTERVAL '300 minutes'")

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

def get_latest_by_fleet_id(vehicle_id: str):
    sql = SQL_LATEST_WITH_PREV_BASE + " WHERE l.vehicle_id = %(vehicle_id)s LIMIT 1;"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"vehicle_id": vehicle_id})
            return cur.fetchone()