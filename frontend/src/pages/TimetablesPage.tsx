import React, { useState, useEffect } from "react";
import { fetchAllRoutes, type AllRoutes, fetchDailyTimetable, type TimetableResponse } from "../api/client";
import { Timetable } from "../components/Timetable";
import { getRouteColors } from "../components/Map";

type Tab = "route" | "stop";

export function TimetablesPage() {
  const [activeTab, setActiveTab] = useState<Tab>("route");
  const [allRoutes, setAllRoutes] = useState<AllRoutes[]>([]);
  
  // Search Inputs
  const [selectedRoute, setSelectedRoute] = useState("");
  const [selectedDirection, setSelectedDirection] = useState(0);
  const [selectedStop, setSelectedStop] = useState("");
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);

  // Results
  const [timetable, setTimetable] = useState<TimetableResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchAllRoutes().then(setAllRoutes).catch(console.error);
  }, []);

  const handleSearchSchedules = async () => {
    if (!selectedRoute) return; // Basic validation
  
    setLoading(true);
    setTimetable(null); 
    try {
      const data = await fetchDailyTimetable(selectedDate, selectedRoute, selectedDirection);
      setTimetable(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Tab Switcher */}
      <div style={{ display: "flex", background: "var(--bg-sub-header)", borderBottom: "1px solid var(--border-color)" }}>
        <button 
          onClick={() => setActiveTab("route")}
          style={tabStyle(activeTab === "route")}
        >🔍 Route Search</button>
        <button 
          onClick={() => setActiveTab("stop")}
          style={tabStyle(activeTab === "stop")}
        >🚏 Stop Search</button>
      </div>

      {/* Search Controls */}
      <div style={{ padding: "15px", display: "flex", gap: "10px", flexWrap: "wrap", alignItems: "flex-end", background: "var(--bg-sub-header)" }}>

        {activeTab === "route" ? (
            <div className="field">
            <label style={labelStyle}>Route | Direction</label>
            <select value={selectedRoute} onChange={(e) => setSelectedRoute(e.target.value)} style={inputStyle}>
                <option value="">Select Route</option>
                {allRoutes.map(r => <option key={r.route_id} value={r.route_id}>{r.route_short_name}</option>)}
            </select>
            <label> </label>
            {/* <label style={labelStyle}>Dir.</label> */}
            <select value={selectedDirection} onChange={(e) => setSelectedDirection(Number(e.target.value))} style={inputStyle}>
                <option value={0}>0 (Inbound)</option>
                <option value={1}>1 (Outbound)</option>
            </select>
            </div>
        ) : (
            // WORK IN PROGRESS
            <div className="field">
            <label style={labelStyle}>Stop</label>
            <select value={selectedRoute} onChange={(e) => setSelectedRoute(e.target.value)} style={inputStyle}>
                <option value="">Select Stop</option>
                {allRoutes.map(r => <option key={r.route_id} value={r.route_id}>{r.route_short_name}</option>)}
            </select>
            </div>
        )}

        <div className="field">
          <label style={labelStyle}>Date</label>
          <input type="date" value={selectedDate} onChange={(e) => setSelectedDate(e.target.value)} style={inputStyle} />
        </div>

        <button onClick={handleSearchSchedules} disabled={loading} style={searchButtonStyle}>
          {loading ? "Searching..." : "Search Timetables"}
        </button>
      </div>

      {/* Timetable Content */}
      <div style={{ marginTop: "20px", padding: "0 15px" }}>
        {/* Only render if timetable is NOT null */}
        {timetable ? (
          <Timetable data={timetable} />
        ) : (
          !loading && (
            <div style={{ textAlign: "center", color: "#666", marginTop: "40px" }}>
              Select a route and date to view the scheduled timetable.
            </div>
          )
        )}
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