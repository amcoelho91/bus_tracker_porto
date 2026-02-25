# Bus Tracker (FIWARE → Postgres → Map)

This project ingests real-time bus positions from FIWARE NGSIv2 and stores:
- full history (`vehicle_observation`)
- latest position per vehicle (`vehicle_latest`)

A backend API serves data to a frontend map. Later we can add stats pages.

## Requirements
- Docker + Docker Compose

## Quick start
1. Create env file:
   ```bash
   cp .env.example .env