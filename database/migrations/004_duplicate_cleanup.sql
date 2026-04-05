-- ROLLBACK;

BEGIN;

-- Part 1: Clean observations
WITH cte1 AS (
    SELECT ctid, ROW_NUMBER() OVER (
        PARTITION BY observed_at, trip_id, heading
        ORDER BY ingested_at DESC
    ) as row_num FROM bus.vehicle_observation
)
DELETE FROM bus.vehicle_observation 
WHERE ctid IN (SELECT ctid FROM cte1 WHERE row_num > 1);

-- Part 2: Clean latest (Notice the semicolon above)
WITH cte2 AS (
    SELECT ctid, ROW_NUMBER() OVER (
        PARTITION BY observed_at, trip_id, heading
        ORDER BY updated_at DESC
    ) as row_num FROM bus.vehicle_latest
)
DELETE FROM bus.vehicle_latest 
WHERE ctid IN (SELECT ctid FROM cte2 WHERE row_num > 1);


-- -- Part 3: Clean bus.vehicle
-- WITH cte3 AS (
--     SELECT ctid, ROW_NUMBER() OVER (
--         PARTITION BY observed_at, trip_id, heading
--         ORDER BY updated_at DESC
--     ) as row_num FROM bus.vehicle
-- )
-- DELETE FROM bus.vehicle_latest 
-- WHERE ctid IN (SELECT ctid FROM cte3 WHERE row_num > 1);

COMMIT;