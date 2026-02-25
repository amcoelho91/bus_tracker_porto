-- 001_init.sql
-- Base schema for FIWARE bus tracking: dimensions + history + realtime latest.

BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;

-- Optional: keep everything in its own schema
CREATE SCHEMA IF NOT EXISTS bus;

-- Static-ish vehicle info (one row per NGSI entity id)
CREATE TABLE IF NOT EXISTS bus.vehicle (
  vehicle_id           text PRIMARY KEY,      -- NGSI entity id (e.g. "urn:ngsi-ld:Vehicle:...")
  fleet_vehicle_id     text,                  -- e.g. "3527"
  name                 text,
  data_provider        text,
  vehicle_type         text,                  -- e.g. "bus"
  source               text,
  created_at           timestamptz NOT NULL DEFAULT now(),
  updated_at           timestamptz NOT NULL DEFAULT now()
);

-- Full history: one row per (vehicle, observation time)
CREATE TABLE IF NOT EXISTS bus.vehicle_observation (
  obs_id               bigserial PRIMARY KEY,
  vehicle_id           text NOT NULL REFERENCES bus.vehicle(vehicle_id) ON DELETE CASCADE,
  observed_at          timestamptz NOT NULL,

  -- extracted from annotations.value entries like "stcp:route:504"
  route_id             text,
  direction            int,
  trip_id              text,

  speed                numeric,
  bearing              int,
  heading              int,
  current_trip_count   int,

  geom                 geometry(Point, 4326) NOT NULL,

  ingested_at          timestamptz NOT NULL DEFAULT now()
);

-- Real-time serving layer: one row per vehicle (upserted)
CREATE TABLE IF NOT EXISTS bus.vehicle_latest (
  vehicle_id           text PRIMARY KEY REFERENCES bus.vehicle(vehicle_id) ON DELETE CASCADE,
  observed_at          timestamptz NOT NULL,

  fleet_vehicle_id     text,
  route_id             text,
  direction            int,
  trip_id              text,

  speed                numeric,
  bearing              int,
  heading              int,

  geom                 geometry(Point, 4326) NOT NULL,
  updated_at           timestamptz NOT NULL DEFAULT now()
);

-- (Optional but useful) Keep track of worker runs for debugging/monitoring
CREATE TABLE IF NOT EXISTS bus.ingest_run (
  run_id               bigserial PRIMARY KEY,
  started_at           timestamptz NOT NULL DEFAULT now(),
  finished_at          timestamptz,
  status               text NOT NULL DEFAULT 'running', -- running/success/error
  fetched_count        int,
  inserted_obs_count   int,
  updated_latest_count int,
  error_message        text
);

COMMIT;