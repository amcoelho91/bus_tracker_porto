import React, { useCallback, useEffect, useMemo, useState } from "react";
import { fetchLatest, type VehicleLatest } from "../api/client";
import { Map } from "../components/Map";
import { VehicleSelector } from "../components/VehicleSelector";

export function MapPage() {
  const [route, setRoute] = useState<string>("704");
  const [direction, setDirection] = useState<number | null>(1); // default like your example
  const [vehicles, setVehicles] = useState<VehicleLatest[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | undefined>(undefined);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const data = await fetchLatest(route, direction);
      setVehicles(data);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (e: any) {
      setError(e?.message ?? "Failed to load");
    }
  }, [route, direction]);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 60_000);
    return () => clearInterval(t);
  }, [refresh]);

  const header = useMemo(() => {
    const n = vehicles.length;
    const d = direction === null ? "all" : String(direction);
    return `${n} vehicle${n === 1 ? "" : "s"} | route ${route || "(all)"} | direction ${d}`;
  }, [vehicles.length, route, direction]);

  return (
    <div style={{ height: "100vh", width: "100vw" }}>
      <VehicleSelector
        route={route}
        onRouteChange={setRoute}
        direction={direction}
        onDirectionChange={setDirection}
        onRefreshNow={refresh}
        lastUpdated={lastUpdated}
      />
      <div style={{ padding: "8px 12px", fontSize: 14, borderBottom: "1px solid #eee" }}>
        <b>{header}</b>
        {error ? <span style={{ marginLeft: 10, color: "crimson" }}>{error}</span> : null}
        <span style={{ marginLeft: 10, color: "#666" }}>
          (green = current, red = previous)
        </span>
      </div>
      <Map vehicles={vehicles} />
    </div>
  );
}