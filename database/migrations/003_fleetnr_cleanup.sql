ROLLBACK;

BEGIN;

-- 1. Remove the old, stubborn constraints
ALTER TABLE bus.vehicle_observation DROP CONSTRAINT IF EXISTS vehicle_observation_vehicle_id_fkey;
ALTER TABLE bus.vehicle_latest DROP CONSTRAINT IF EXISTS vehicle_latest_vehicle_id_fkey;

-- 2. Drop the redundant parent table
DROP TABLE IF EXISTS bus.vehicle CASCADE;

-- 3. Clean the IDs in your existing data
UPDATE bus.vehicle_observation SET vehicle_id = regexp_replace(vehicle_id, '^.*:', '') WHERE vehicle_id LIKE 'urn:%';
UPDATE bus.vehicle_latest SET vehicle_id = regexp_replace(vehicle_id, '^.*:', '') WHERE vehicle_id LIKE 'urn:%';

-- 4. Finally, drop the fleet_vehicle_id columns
ALTER TABLE bus.vehicle_latest DROP COLUMN IF EXISTS fleet_vehicle_id;


COMMIT;