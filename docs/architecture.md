# Architecture

This project ingests real-time bus location data from a FIWARE NGSIv2 broker, stores it in Postgres/PostGIS, and serves it to a frontend map and (later) analytics pages.

## Goals

1. **Real-time map**: show the latest position of vehicles on a given route (e.g., route `704`) quickly.
2. **Historical analytics**: keep an append-only history so we can later compute statistics such as travel time by hour-of-day and day-of-week.

## High-level components

### 1) FIWARE Broker (external)
- Source of truth for current vehicle entities.
- Polled every minute by our worker.

### 2) Worker (backend_worker)
- **Fetches** the FIWARE endpoint every `POLL_SECONDS` (default 60 seconds).
- **Parses** the response and extracts:
  - identifiers (NGSI `id`, `fleetVehicleId`)
  - observation timestamp (`observationDateTime`)
  - geometry (`location`)
  - optional operational context from `annotations` (e.g., `stcp:route`, `stcp:sentido`, `stcp:nr_viagem`)
- **Writes** to the database:
  - appends to `bus.vehicle_observation` (history)
  - upserts into `bus.vehicle_latest` (one row per vehicle, only if the record is newer)

### 3) Database (db)
Postgres + PostGIS.

**Tables (current)**
- `bus.vehicle`  
  Static-ish vehicle metadata keyed by `vehicle_id` (NGSI id). Updated on each ingest.
- `bus.vehicle_observation`  
  Append-only history (vehicle_id, observed_at, route_id, geom, etc.).
- `bus.vehicle_latest`  
  Latest row per vehicle for fast map queries.
- `bus.ingest_run` (optional)  
  Worker run log for debugging and monitoring.

**Why two fact tables?**
- `vehicle_latest` is the **serving layer** for real-time (fast reads, small table).
- `vehicle_observation` is the **historical store** for analytics (large table, time-series).

### 4) API (backend_api)
FastAPI service that reads from Postgres and provides endpoints for the frontend.

### 5) Frontend (frontend)
React + Leaflet app that:
- polls API for latest vehicles on a route
- renders markers on an OpenStreetMap tile layer
- later will add stats dashboards

## Data flow

1. Worker polls FIWARE: `GET /v2/entities?...`
2. Worker writes:
   - `bus.vehicle` upsert
   - `bus.vehicle_observation` insert (deduped if unique index is enabled)
   - `bus.vehicle_latest` upsert with `WHERE EXCLUDED.observed_at > v.observed_at`
3. Frontend polls API:
   - `GET /api/latest?route=704`
4. API queries:
   - `SELECT ... FROM bus.vehicle_latest WHERE route_id = '704'`

## Deployment & runtime

Everything runs via Docker Compose:
- `db` (Postgres/PostGIS)
- `backend_worker` (Python worker)
- `backend_api` (FastAPI)
- `frontend` (Vite dev server)

Environment variables are managed through `.env`.

## Future: travel-time statistics

To compute “how long routes take by hour-of-day and day-of-week”, we will add:

1. A derived table `bus.trip_run` computed from `vehicle_observation` using:
   - route_id + vehicle_id + trip_id (+ direction)
   - boundary detection when trip_id changes, route changes, or a long gap occurs
2. Rollups:
   - materialized view or table such as `bus.route_travel_time_stats`
   - grouped by `route_id`, `direction`, `EXTRACT(DOW)`, `EXTRACT(HOUR)`
   - metrics: count, avg, p50, p90, etc.

The current schema is designed to support this without changing the ingestion pipeline.