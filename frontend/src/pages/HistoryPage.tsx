import React, { useState, useEffect } from "react";
import { fetchAllRoutes, type AllRoutes, type VehicleLatest, type RouteShape, 
    fetchRouteShape, fetchHistory, fetchAvailableTrips } from "../api/client";
import { HistoryMap } from "../components/HistoryMap";

type Tab = "trip" | "route";

export function HistoryPage() {
  const [activeTab, setActiveTab] = useState<Tab>("trip");
  const [allRoutes, setAllRoutes] = useState<AllRoutes[]>([]);
  
  // Search Inputs
  const [selectedRoute, setSelectedRoute] = useState("");
  const [selectedTrip, setSelectedTrip] = useState("");
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [startTime, setStartTime] = useState("12:00");
  const [endTime, setEndTime] = useState("14:00");

  // Results
  const [historyData, setHistoryData] = useState<VehicleLatest[]>([]);
  const [availableTrips, setAvailableTrips] = useState<string[]>([]);
  const [shape, setShape] = useState<RouteShape | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchAllRoutes().then(setAllRoutes).catch(console.error);
  }, []);

  // Effect to fetch trips when parameters change
  useEffect(() => {
    console.log("Checking for trips:", { selectedRoute, selectedDate, activeTab });
    if (selectedRoute && selectedDate && activeTab === "trip") {
      fetchAvailableTrips(selectedRoute, selectedDate)
        .then(setAvailableTrips)
        .catch(() => setAvailableTrips([]));
    } else {
      setAvailableTrips([]);
    }
  }, [selectedRoute, selectedDate, activeTab]);

  const handleSearch = async () => {
    setHistoryData([]); // Clear the map immediately
    setLoading(true);
    try {
      // TODO: Implement fetchHistory in your api/client.ts
      const data = await fetchHistory({ 
        mode: activeTab,
        route_id: selectedRoute,
        trip_id: selectedTrip, 
        date: selectedDate,
        start_time: startTime, 
        end_time: endTime
      });
      setHistoryData(data);
      
      // Also fetch shape to provide context on the map
      if (selectedRoute) {
        const shapeData = await fetchRouteShape(selectedRoute, 1); // Defaulting to direction 1 for now
        setShape(shapeData);
      }
    } catch (e) {
      alert("Search failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Tab Switcher */}
      <div style={{ display: "flex", background: "var(--bg-sub-header)", borderBottom: "1px solid var(--border-color)" }}>
        <button 
          onClick={() => setActiveTab("trip")}
          style={tabStyle(activeTab === "trip")}
        >🔍 Trip Search</button>
        <button 
          onClick={() => setActiveTab("route")}
          style={tabStyle(activeTab === "route")}
        >🛤️ Route Search [WIP]</button>
      </div>

      {/* Search Controls */}
      <div style={{ padding: "15px", display: "flex", gap: "10px", flexWrap: "wrap", alignItems: "flex-end", background: "white" }}>
        <div className="field">
          <label style={labelStyle}>Route</label>
          <select value={selectedRoute} onChange={(e) => setSelectedRoute(e.target.value)} style={inputStyle}>
            <option value="">Select Route</option>
            {allRoutes.map(r => <option key={r.route_id} value={r.route_id}>{r.route_short_name}</option>)}
          </select>
        </div>

        {activeTab === "trip" ? (
          <div className="field">
            <label style={labelStyle}>Trip ID</label>
            <select value={selectedTrip} onChange={(e) => setSelectedTrip(e.target.value)} style={inputStyle} disabled={availableTrips.length === 0}>
                <option value="">
                    {availableTrips.length > 0 ? "Select a Trip" : "No trips found for this day"}
                </option>
                {availableTrips.map(tid => (
                    <option key={tid} value={tid}>{tid}</option>
                ))}
            </select>
          </div>
        ) : (
          <>
            <div className="field">
              <label style={labelStyle}>Start Time</label>
              <input type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} style={inputStyle} />
            </div>
            <div className="field">
              <label style={labelStyle}>End Time</label>
              <input type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} style={inputStyle} />
            </div>
          </>
        )}

        <div className="field">
          <label style={labelStyle}>Date</label>
          <input type="date" value={selectedDate} onChange={(e) => setSelectedDate(e.target.value)} style={inputStyle} />
        </div>

        <button onClick={handleSearch} disabled={loading} style={searchButtonStyle}>
          {loading ? "Searching..." : "Search History"}
        </button>
      </div>

      {/* Map Content */}
      <div style={{ flex: 1, position: "relative" }}>
        <HistoryMap 
          vehicles={historyData} 
          shapeData={shape} 
          selectedRoute={selectedRoute} 
        />
      </div>
    </div>
  );
}

// Simple Styles
const tabStyle = (active: boolean) => ({
  padding: "10px 20px",
  cursor: "pointer",
  border: "none",
  background: active ? "white" : "transparent",
  borderBottom: active ? "2px solid #0b5" : "2px solid transparent",
  fontWeight: active ? "bold" : "normal",
  color: active ? "#000000" : "#999999",
  transition: "all 0.2s ease",
});

const labelStyle: React.CSSProperties = { display: "block", fontSize: "11px", fontWeight: "bold", marginBottom: "4px" };
const inputStyle = { padding: "6px", borderRadius: "4px", border: "1px solid #ccc" };
const searchButtonStyle = { padding: "8px 16px", background: "#0b5", color: "white", border: "none", borderRadius: "4px", cursor: "pointer" };