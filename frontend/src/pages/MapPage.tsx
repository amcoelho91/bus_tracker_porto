import React, { useCallback, useEffect, useMemo, useState } from "react";
import { fetchLatest, fetchRouteShape, fetchAllRoutes, fetchStops,
   type VehicleLatest, type RouteShape, type AllRoutes, type Stop } from "../api/client";
import { Map, getRouteColors } from "../components/Map";
import { VehicleSelector } from "../components/VehicleSelector";

export function MapPage() {
  const [route, setRoute] = useState<string>("704");
  const [direction, setDirection] = useState<number | null>(1); // default like your example
  const [vehicles, setVehicles] = useState<VehicleLatest[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | undefined>(undefined);
  const [shapeData0, setShapeData0] = useState<RouteShape | null>(null);
  const [shapeData1, setShapeData1] = useState<RouteShape | null>(null);
  const [allRoutes, setAllRoutes] = useState<AllRoutes[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [isListOpen, setIsListOpen] = useState(false);
  const [stops, setStops] = useState<Stop[]>([]);
  const [selectedRoute, setSelectedRoute] = useState<string>("");
  const [selectedDirection, setSelectedDirection] = useState<number | null>(null);

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

  useEffect(() => {
    async function loadShape() {
      // If route is empty/null (All Routes), clear shapes and stop
      if (!route || route === "") {
        setShapeData0(null);
        setShapeData1(null);
        return;
      }

      if (direction === null) {
        const [data0, data1] = await Promise.all([
          fetchRouteShape(route, 0),
          fetchRouteShape(route, 1)
        ]);
        setShapeData0(data0);
        setShapeData1(data1);
      } else {
        const data = await fetchRouteShape(route, direction);
        setShapeData0(data);
        setShapeData1(null);
      }
    }
    loadShape();
  }, [route, direction]);
  
  // Fetch the routes once when the page mounts
  useEffect(() => {
    async function loadRoutes() {
      try {
        const data = await fetchAllRoutes();
        setAllRoutes(data);
      } catch (e) {
        console.error("Could not load routes list", e);
      }
    }
    loadRoutes();
  }, []);

  useEffect(() => {
    async function loadStops() {
      // Check if 'route' has a value. 
      // We'll be more flexible with 'direction' in case it's 0.
      if (route) {
        console.log(`🔍 Fetching stops for Route: ${route}, Direction: ${direction}`);
        try {
          const data = await fetchStops(route, direction);
          setStops(data);
        } catch (err) {
          console.error("Failed to load stops:", err);
        }
      } else {
        setStops([]);
      }
    }
    loadStops();
  }, [route, direction]);

  const header = useMemo(() => {
    const n = vehicles.length;
    // pedropt10: Added Ida and Volta labels
    let directionLabel;
      if (direction === 0) {
        directionLabel = '0 ("Ida")';
      } else if (direction === 1) {
        directionLabel = '1 ("Volta")';
      } else {
        directionLabel = "(all)";
      }

    const d = direction === null ? "all" : String(direction);
    const routeDisplay = route === "" || !route ? "(all)" : route;
    
    return `${n} vehicle${n === 1 ? "" : "s"} | route ${route || "(all)"} | direction ${directionLabel}`;
  }, [vehicles.length, route, direction]);

  const mostRecentLocationTime = useMemo(() => {
    if (!vehicles || vehicles.length === 0) return undefined; 
    
    // Find the max timestamp
    const timestamps = vehicles.map(v => new Date(v.observed_at).getTime());
    if (timestamps.length === 0) return undefined;
    
    const maxTs = Math.max(...timestamps);
    return new Date(maxTs).toLocaleTimeString('pt-PT', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  }, [vehicles]);

  // Update your filteredRoutes to use the live data
  const filteredRoutes = useMemo(() => {
    return allRoutes.filter(r => 
      r.route_id.toLowerCase().includes(searchTerm.toLowerCase()) || 
      r.route_short_name.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [searchTerm, allRoutes]);

    return (
    <div style={{ height: "100vh", width: "100vw", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <VehicleSelector
        route={route}
        onRouteChange={setRoute}
        direction={direction}
        onDirectionChange={setDirection}
        onRefreshNow={refresh}
        lastUpdated={lastUpdated}
        mostRecentLocation={mostRecentLocationTime}
        allRoutes={allRoutes}
      />
      {/* <div style={{ padding: "4px 12px", fontSize: 13, borderBottom: "1px solid #eee", background: "#f9f9f9" }}> */}
      <div style={{ padding: "4px 12px", fontSize: 13, borderBottom: "1px solid var(--border-color)", 
                    background: "var(--bg-sub-header)", color: "var(--text-main)" }}>
        <b>{header}</b>
        {error && <span style={{ marginLeft: 10, color: "crimson" }}>{error}</span>}
      </div>
      {/* <div style={{ padding: "10px", position: "relative", zIndex: 1000, background: "white" }}>
        <input 
          type="text" 
          placeholder="Search Route (e.g. 704)..."
          value={searchTerm}
          onFocus={() => setIsListOpen(true)}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{ width: "100%", padding: "8px" }}
        />
        
        {isListOpen && filteredRoutes.length > 0 && (
          <div style={{ 
            position: "absolute", top: "100%", left: 10, right: 10, 
            maxHeight: "250px", overflowY: "auto", background: "white", 
            border: "1px solid #ccc", boxShadow: "0 4px 6px rgba(0,0,0,0.1)" 
          }}>
            {filteredRoutes.map((r) => {
              const { bgColor, textColor } = getRouteColors(r.route_id, 1);
              return (
                <div 
                  key={r.route_id}
                  onClick={() => {
                    setRoute(r.route_id);
                    setSearchTerm(r.route_short_name);
                    setIsListOpen(false);
                  }}
                  style={{ padding: "8px", cursor: "pointer", borderBottom: "1px solid #eee" }}
                >
                  <span style={{ backgroundColor: bgColor, color: textColor, padding: "2px 6px", display: "inline-block" }}>
                    <b>{r.route_short_name}</b>
                  </span>
                  &nbsp; {r.route_long_name}
                </div>
              );
            })}
          </div>
        )}
      </div> */}
      <div style={{ flex: 1, position: "relative" }}>
        <Map vehicles={vehicles} shapeData0={shapeData0} shapeData1={shapeData1} stops={stops} selectedRoute={route} selectedDirection={direction} />
      </div>
    </div>
  );
}