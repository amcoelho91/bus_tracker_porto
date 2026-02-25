# Database

This folder contains SQL migrations used to initialize the Postgres/PostGIS schema.

## Migrations
- `migrations/001_init.sql` creates schema + core tables:
  - `bus.vehicle` (vehicle entity metadata)
  - `bus.vehicle_observation` (append-only history)
  - `bus.vehicle_latest` (one row per vehicle, upserted by worker)
  - `bus.ingest_run` (optional worker run log)

- `migrations/002_indexes.sql` adds indexes and a uniqueness guard for history.

These migrations are mounted into the Postgres container and executed automatically on first database creation via:
`/docker-entrypoint-initdb.d/`.

## Seed
`seed/` is optional and can contain dev-only inserts (routes list, fixtures, etc.)