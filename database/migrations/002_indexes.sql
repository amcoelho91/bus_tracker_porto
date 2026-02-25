-- 002_indexes.sql
-- Indexes + constraints for performance and data quality.

BEGIN;

-- HISTORY: fast "latest for a vehicle", time range scans, and route filtering
CREATE INDEX IF NOT EXISTS ix_obs_vehicle_time
  ON bus.vehicle_observation (vehicle_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS ix_obs_route_time
  ON bus.vehicle_observation (route_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS ix_obs_observed_at
  ON bus.vehicle_observation (observed_at DESC);

-- If you will do map bounding box queries on history
CREATE INDEX IF NOT EXISTS ix_obs_geom
  ON bus.vehicle_observation USING gist (geom);

-- LATEST: fast lookups by route + geo
CREATE INDEX IF NOT EXISTS ix_latest_route
  ON bus.vehicle_latest (route_id);

CREATE INDEX IF NOT EXISTS ix_latest_time
  ON bus.vehicle_latest (observed_at DESC);

CREATE INDEX IF NOT EXISTS ix_latest_geom
  ON bus.vehicle_latest USING gist (geom);

-- Optional: prevent accidental exact duplicates in history.
-- This is safe if FIWARE doesn't send multiple identical timestamps per vehicle.
-- If you suspect duplicates, keep it. If you see conflicts, drop it.
CREATE UNIQUE INDEX IF NOT EXISTS ux_obs_vehicle_observed_at
  ON bus.vehicle_observation (vehicle_id, observed_at);

COMMIT;