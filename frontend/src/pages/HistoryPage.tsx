import React, { useState, useEffect, useMemo } from "react";
import { fetchAllRoutes, fetchAvailableTrips, fetchHistory, fetchStops, fetchTripShape, fetchTripOrigin, fetchTripExecution,
type AllRoutes, type VehicleLatest, type TripShape, type TripOriginResponse, type TripExecution, type Stop, } from "../api/client";
import { HistoryMap } from "../components/HistoryMap";
import { TripSpine } from "../components/HistorySpine";
import { getRouteColors, getDirectionDestination } from "../components/Map";

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
  const [tripOrigin, setTripOrigin] = useState<TripOriginResponse[]>([]);
  const [tripExecution, setTripExecution] = useState<TripExecution[]>([]);
  const [shape, setShape] = useState<TripShape | null>(null);
  const [stops, setStops] = useState<Stop[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedRouteColors, setRouteColors] = useState({ bgColor: 'transparent', textColor: 'inherit' });

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
    if (!selectedRoute || (activeTab === "trip" && !selectedTrip)) {
      alert(`Please select ${activeTab === "trip" ? "both a Route and a Trip" : "a Route"} before searching!`);
      return; // Exit function early
    }
     // Clear the map immediately, as well as the trip origin and the execution data
    setHistoryData([]);
    setTripOrigin([]);
    setTripExecution([]);
    setStops([]);
    setLoading(true);
    try {
      // 1. Fetch main history data (GPS points for the map)
      const data = await fetchHistory({ 
        mode: activeTab,
        route_id: selectedRoute,
        trip_id: selectedTrip, 
        date: selectedDate,
        start_time: startTime, 
        end_time: endTime
      });
      setHistoryData(data);
      
      // 2. Fetch Trip Shape
      if (selectedTrip) {
        const shapeData = await fetchTripShape(selectedTrip);
        setShape(shapeData);
        const data = await fetchStops(selectedRoute, 0);
        setStops(data);
        // DIRECTION TEMPORARILY SET AS ZER O
        // Must be modified to get the stops via the shape_id 
      }

      // 3. Fetch Route Colors
      if (selectedRoute) {
        const selectedRouteColors = getRouteColors(selectedRoute, 0);
          setRouteColors({
            bgColor: selectedRouteColors.bgColor || 'transparent',
            textColor: selectedRouteColors.textColor || '(var--text-main)'
          });
      }

      // 4. Fetch Trip Context (Origin and Spine Execution)
      if (selectedTrip) {
        // Run these in parallel to save time
        const [origin, exec] = await Promise.all([
          fetchTripOrigin(selectedTrip),
          fetchTripExecution(selectedTrip, selectedDate)
        ]);
        
        setTripOrigin([origin]);
        setTripExecution(exec);
      }
      // if (selectedTrip) {
      //   const tripOrigin = await fetchTripOrigin(selectedTrip);
      //   setTripOrigin([tripOrigin]);
      // }

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
      <div style={{ padding: "15px", display: "flex", gap: "10px", flexWrap: "wrap", 
        alignItems: "flex-end", background: "var(--bg-sub-header)", borderBottom: "1px solid var(--border-color)" }}>
        <div className="field">
          <label style={labelStyle}>Route</label>
          <select value={selectedRoute} onChange={(e) => {
            setSelectedRoute(e.target.value); 
            setSelectedTrip(""); // Reset the trip whenever the route changes
          }} style={inputStyle}>
            <option value="">Select Route</option>
            {allRoutes.map(r => <option key={r.route_id} value={r.route_id}>{r.route_short_name}</option>)}
          </select>
        </div>

        {activeTab === "trip" ? (
          <div className="field">
            <label style={labelStyle}>Trip ID</label>
            <select value={selectedTrip} onChange={(e) => setSelectedTrip(e.target.value)} style={inputStyle} disabled={availableTrips.length === 0}>
                <option value="" hidden={!!selectedTrip}>
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

      {/* Trip Header */}
      <div style={{ height: "75px", display: "flex", gap: "10px", flexWrap: "wrap", padding: "15px",
        alignItems: "flex-end", background: "var(--bg-sub-header)", borderBottom: "1px solid var(--border-color)"}}>
          {selectedRoute && (
            <>
              {historyData[0]?.route_short_name ? (
                <span style={{ backgroundColor: selectedRouteColors.bgColor, color: selectedRouteColors.textColor, padding: "2px 2px", borderRadius: 10, minWidth: 80,
                            display: "inline-block", textAlign: "center", fontSize: "32px"}}>
                            <b>{historyData[0]?.route_short_name || " "}</b> </span> 
                          ) : ( " " ) }

              {/* Table-like Container for the Headsign and Subtext */}
              {/* <div style={{ display: "flex", flexDirection: "column", justifyContent: "flex-end", height: "100%", margin: 0, padding: 0 }}> */}

                  {/* First Row: Trip Headsign */}
                {/* <span style={{ fontSize: "24px", lineHeight: "1", color: "var(--text-main)" }}>
                  <b>→&nbsp;{historyData[0]?.trip_headsign || " "}</b>
                </span> */}

                {/* Second Row: Placeholder Text */}
                {/* <span style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: "1.2" }}>
                  Origin: {tripOrigin[0]?.origin_stop_name}
                </span> */}

              {/* </div> */}
              <span style={{ textAlign: "center", fontSize: "24px", paddingBottom: "8px" }}>
                {(historyData[0]?.trip_headsign && tripOrigin[0]?.origin_stop_name) ? (
                  <>
                    {tripOrigin[0]?.origin_stop_name}
                    <b>&nbsp;→&nbsp;{historyData[0]?.trip_headsign}</b>
                  </>
                ) : ( " " )} </span>
            </>
            )}
      </div>

      {/* Main Content Area: Side-by-Side Wrapper */}
      <div style={{ 
        display: "flex", 
        flexDirection: "row", // Horizontal layout
        flex: 1, 
        width: "100%", 
        overflow: "hidden", // Keeps the scroll within the children
        background: "var(--bg-main)"
      }}>

        {/* Left Column: Trip Spine */}
        {tripExecution.length > 0 && (
          <div style={{ 
            flex: "2",             // Takes 1 share of space
            minWidth: "320px",     // Prevents it from getting too squished
            maxWidth: "450px",     // Prevents it from getting too wide on huge monitors
            borderRight: "1px solid var(--border-color)", 
            overflowY: "auto",      // Only the spine scrolls
            background: "var(--bg-nav)"
          }}>
            <TripSpine 
              execution={tripExecution} 
              routeColors={selectedRouteColors} 
            />
          </div>
        )}

        {/* Right Column: Map Content */}
        <div style={{ 
          flex: "5",               // Takes 3 shares (Map will be ~75% width)
          position: "relative",
          height: "100%"
        }}>
          <HistoryMap 
            vehicles={historyData} 
            shapeData={shape} 
            selectedRoute={selectedRoute} 
            stops={stops}
          />
        </div>

      </div>

      <div style={{ minHeight: "60px"}}>&nbsp;</div>

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