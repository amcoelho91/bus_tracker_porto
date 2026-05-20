-- 001_init.sql
-- Base schema for FIWARE bus tracking: dimensions + history + realtime latest.
-- Other schema for static GTFS data (routes, shapes, stops, trips, ...)

BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS bus;
CREATE SCHEMA IF NOT EXISTS gtfs;

-- Full history: one row per (vehicle, observation time)
CREATE TABLE IF NOT EXISTS bus.vehicle_observation (
  obs_id               bigserial PRIMARY KEY,
  vehicle_id           text NOT NULL,
  observed_at          timestamptz NOT NULL,

  -- extracted from annotations.value entries like "stcp:route:504"
  route_id             text,
  direction            int,
  trip_id              text,

  heading              int,
  current_trip_count   int,

  geom                 geometry(Point, 4326) NOT NULL,

  ingested_at          timestamptz NOT NULL DEFAULT now(),
  
  last_stop_id          text,
  cur_stop_id           text
);

-- Real-time serving layer: one row per vehicle (upserted)
CREATE TABLE IF NOT EXISTS bus.vehicle_latest (
  vehicle_id           text PRIMARY KEY,
  observed_at          timestamptz NOT NULL,

  route_id             text,
  direction            int,
  trip_id              text,

  heading              int,

  geom                 geometry(Point, 4326) NOT NULL,
  updated_at           timestamptz NOT NULL DEFAULT now(),

  last_stop_id          text,
  cur_stop_id           text
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

CREATE TABLE IF NOT EXISTS bus.fleet (
    vehicle_id TEXT PRIMARY KEY,
    vehicle_license_plate TEXT,
    vehicle_type TEXT,
    vehicle_fuel TEXT,
    vehicle_model TEXT,
    vehicle_chassis_year INTEGER
);

CREATE TABLE IF NOT EXISTS gtfs.routes (
    route_id TEXT PRIMARY KEY,
    route_short_name TEXT,
    route_long_name TEXT,
    route_color TEXT,
    route_text_color TEXT
);

CREATE TABLE IF NOT EXISTS gtfs.shapes (
    shape_id TEXT PRIMARY KEY,
    route_id TEXT,
    direction_id INTEGER,
    variant_id INTEGER,
    geom geometry(LineString, 4326),
    shape_dist_traveled DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS gtfs.stops (
    stop_id TEXT PRIMARY KEY,
    stop_name TEXT NOT NULL,
    stop_lat DOUBLE PRECISION NOT NULL,
    stop_lon DOUBLE PRECISION NOT NULL,
    zone_id TEXT,
    stop_url TEXT
);

CREATE TABLE IF NOT EXISTS gtfs.trips (
    trip_id TEXT PRIMARY KEY,
    route_id TEXT REFERENCES gtfs.routes(route_id),
    direction_id INTEGER,
    service_id TEXT,
    trip_headsign TEXT,
    shape_id TEXT REFERENCES gtfs.shapes(shape_id),
    shift_nr INTEGER, -- comes from T in trip_id
    trip_nr_in_shift INTEGER  -- comes from N in trip_id
);

CREATE TABLE IF NOT EXISTS gtfs.stop_times (
    trip_id TEXT REFERENCES gtfs.trips(trip_id) ON DELETE CASCADE,
    arrival_time TEXT,
    departure_time TEXT,
    stop_id TEXT REFERENCES gtfs.stops(stop_id) ON DELETE CASCADE,
    stop_sequence INTEGER NOT NULL,
    shape_dist_traveled DOUBLE PRECISION,
    timepoint BOOLEAN,
    PRIMARY KEY (trip_id, stop_sequence)
);

-- Optimized Mapping from shape_id to stop_id sequence for quick lookups
-- This allows the frontend to quickly find all stops for a specific shape
CREATE TABLE IF NOT EXISTS gtfs.shape_stops (
    shape_id TEXT,
    stop_id TEXT REFERENCES gtfs.stops(stop_id),
    stop_sequence INTEGER,
    shape_dist_traveled DOUBLE PRECISION,
    PRIMARY KEY (shape_id, stop_sequence)
);

CREATE TABLE IF NOT EXISTS gtfs.calendar (
    service_id TEXT PRIMARY KEY,
    monday INTEGER,
    tuesday INTEGER,
    wednesday INTEGER,
    thursday INTEGER,
    friday INTEGER,
    saturday INTEGER,
    sunday INTEGER,
    start_date TEXT,
    end_date TEXT
);

CREATE TABLE IF NOT EXISTS gtfs.calendar_dates (
    service_id TEXT,
    date TEXT,
    exception_type INTEGER,
    PRIMARY KEY (service_id, date)
);

COMMIT;