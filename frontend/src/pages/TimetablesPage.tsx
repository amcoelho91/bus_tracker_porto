import React, { useState, useEffect, useMemo } from "react";
import { fetchAllRoutes, type AllRoutes, fetchDailyTimetable, type TimetableResponse } from "../api/client";
import { Timetable } from "../components/Timetable";
import { getRouteColors } from "../components/Map";

type Tab = "routeTab" | "stop";

// WORK IN PROGRESS: ROUTES DROP-DOWN WITH FORMATTED ROUTE IDS
//    Several unused elements are in the script, due to the attempted implementation of this
//    A drop-down as in the Map page should be implemented in this Timetables Page.

export function TimetablesPage() {
  const [activeTab, setActiveTab] = useState<Tab>("routeTab");
  const [allRoutes, setAllRoutes] = useState<AllRoutes[]>([]);
  const [isListOpen, setIsListOpen] = useState(false);
    
  // Search Inputs
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedRoute, setSelectedRoute] = useState("");
  const [selectedDirection, setSelectedDirection] = useState(0);
  const [selectedStop, setSelectedStop] = useState("");
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);

  const selectedRouteObj = useMemo(() => 
      allRoutes.find(r => r.route_id === selectedRoute), 
    [selectedRoute, allRoutes]);

  // Filter routes based on what the user is typing
  const filteredRoutes = useMemo(() => {
    if (!searchTerm) return allRoutes;
    return allRoutes.filter(r => 
      r.route_id.toLowerCase().includes(searchTerm.toLowerCase()) || 
      r.route_short_name.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [searchTerm, allRoutes]);

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

  // Get colors for the currently selected route (or defaults if none)
  const { bgColor, textColor } = useMemo(() => {
      if (!selectedRouteObj) return { bgColor: 'transparent', textColor: 'inherit' };
      return getRouteColors(selectedRouteObj.route_id, 0);
    }, [selectedRouteObj]);

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Tab Switcher */}
      <div style={{ display: "flex", background: "var(--bg-sub-header)", borderBottom: "1px solid var(--border-color)" }}>
        <button 
          onClick={() => setActiveTab("routeTab")}
          style={tabStyle(activeTab === "routeTab")}
        >🔍 Route Search</button>
        <button 
          onClick={() => setActiveTab("stop")}
          style={tabStyle(activeTab === "stop")}
        >🚏 Stop Search</button>
      </div>

      {/* Search Controls */}
      {/* <div style={{ padding: "15px", display: "flex", gap: "10px", flexWrap: "wrap", alignItems: "flex-end", background: "var(--bg-sub-header)" }}> */}
      <div style={{ padding: "15px", display: "flex", gap: "10px", flexWrap: "wrap", alignItems: "flex-end", background: "var(--bg-sub-header)" }}>
        {activeTab === "routeTab" ? (
            <div className="field">
              <label style={styles.label}>Route | Direction</label>
              <select value={selectedRoute} onChange={(e) => setSelectedRoute(e.target.value)} style={styles.input}>
                  <option value="">Select Route</option>
                  {allRoutes.map(r => <option key={r.route_id} value={r.route_id}>{r.route_short_name}</option>)}
              </select>
                                
              <label> </label>
              {/* <label style={styles.label}>Dir.</label> */}
              <select value={selectedDirection} onChange={(e) => setSelectedDirection(Number(e.target.value))} style={styles.input}>
                  <option value={0}>0 (Inbound)</option>
                  <option value={1}>1 (Outbound)</option>
              </select>
            </div>
        ) : (
            // WORK IN PROGRESS
            <div className="field">
            <label style={styles.label}>Stop</label>
            <select value={selectedRoute} onChange={(e) => setSelectedRoute(e.target.value)} style={styles.input}>
                <option value="">Select Stop</option>
                {allRoutes.map(r => <option key={r.route_id} value={r.route_id}>{r.route_short_name}</option>)}
            </select>
            </div>
        )}

        <div className="field">
          <label style={styles.label}>Date</label>
          <input type="date" value={selectedDate} onChange={(e) => setSelectedDate(e.target.value)} style={styles.input} />
        </div>

        <button onClick={handleSearchSchedules} disabled={loading} style={styles.button}>
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
              Select a Route and date to view the scheduled timetable.
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

// const styles.label: React.CSSProperties = { display: "block", fontSize: "11px", fontWeight: "bold", marginBottom: "4px" };
// const styles.input = { padding: "6px", borderRadius: "4px", border: "1px solid #ccc" };
const styles: Record<string, React.CSSProperties> = {
  left: { display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" },
  button: {
    padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border-color)",
    background: "var(--bg-button)", color: "var(--text-main)", cursor: "pointer"
  },
  label: { display: "block", fontSize: "11px", fontWeight: "bold", marginBottom: "4px" },
  input: { padding: "6px", borderRadius: "4px", border: "1px solid var(--border-color)", 
    background: "var(--bg-input-select)", color: "var(--text-main)" },
  select: { padding: "6px 8px", border: "1px solid var(--border-color)", borderRadius: 6, 
    background: "var(--bg-input-select)", color: "var(--text-main)" },
  dropdown: {
    position: "absolute", top: "100%", 
    left: 45, // Adjusted to align with the start of the input
    width: 300, maxHeight: 300, overflowY: "auto",
    backgroundColor: "var(--bg-nav)", border: "1px solid var(--border-color)", borderRadius: 4,
    boxShadow: "0 4px 12px rgba(0,0,0,0.15)", zIndex: 2000, marginTop: 4
  },
  dropdownItem: {
    padding: "8px 12px", cursor: "pointer",
    fontSize: 13, borderBottom: "1px solid var(--border-color)",
    color: "var(--text-main)", backgroundColor: "var(--bg-sub-header)",
    whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis"
  }
};