SELECT 
    route_id, 
    COUNT(*) as total_obs,
    COUNT(last_stop_id) as matched_stops,
    ROUND((COUNT(last_stop_id)::float / COUNT(*)::float) * 100) as success_rate_percent
FROM bus.vehicle_observation
WHERE observed_at > NOW() - INTERVAL '10 minutes'
GROUP BY route_id
ORDER BY success_rate_percent DESC;