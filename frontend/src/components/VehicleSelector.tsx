import React, { useState, useMemo } from "react";
import { getRouteColors } from "./Map";
import { AllRoutes } from "../api/client";

type Props = {
  route: string;
  onRouteChange: (route: string) => void;
  allRoutes: AllRoutes[];

  direction: number | null; // null = all
  onDirectionChange: (direction: number | null) => void;

  onRefreshNow: () => void;
  lastUpdated?: string;
  mostRecentLocation?: string;  //
};

export function VehicleSelector({
  route,
  onRouteChange,
  allRoutes,
  direction,
  onDirectionChange,
  onRefreshNow,
  lastUpdated,
  mostRecentLocation
}: Props) {
  const [searchTerm, setSearchTerm] = useState("");
  const [isListOpen, setIsListOpen] = useState(false);
  
  const selectedRouteObj = useMemo(() => 
      allRoutes.find(r => r.route_id === route), 
    [route, allRoutes]);

  // Filter routes based on what the user is typing
  const filteredRoutes = useMemo(() => {
    if (!searchTerm) return allRoutes;
    return allRoutes.filter(r => 
      r.route_id.toLowerCase().includes(searchTerm.toLowerCase()) || 
      r.route_short_name.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [searchTerm, allRoutes]);

  // Get colors for the currently selected route (or defaults if none)
  const { bgColor, textColor } = useMemo(() => {
      if (!selectedRouteObj) return { bgColor: 'transparent', textColor: 'inherit' };
      return getRouteColors(selectedRouteObj.route_id, 0);
    }, [selectedRouteObj]);

  return (
    <div style={styles.bar}>
      <div style={styles.left}>
        <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
          <span style={{ fontSize: 14 }}>Route:&nbsp;</span>
          <div style={{ 
            position: "relative",  display: "flex", alignItems: "center",
            background: "white", border: "1px solid var(--border-color)", borderRadius: 4,
            padding: "2px 4px",  minWidth: 120, cursor: "text"
          }} 
          onClick={() => setIsListOpen(true)}>
            
            {/* 1. Selected route box (Visible when list is closed and route is selected) */}
            {!isListOpen && selectedRouteObj && (
              <span style={{ 
                backgroundColor: bgColor, color: textColor, padding: "2px 6px", 
                borderRadius: 4, fontSize: 14, fontWeight: "bold", marginRight: 4                
              }}>
                {selectedRouteObj.route_short_name}
              </span>
            )}

            {/* 2. THE SEARCH INPUT */}
            <input
              value={isListOpen ? searchTerm : (selectedRouteObj ? "" : route)}
              onFocus={() => {
                setIsListOpen(true);
                setSearchTerm("");
              }}
              onBlur={() => setTimeout(() => setIsListOpen(false), 200)}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder={!selectedRouteObj ? "Search..." : ""}
              style={{ 
                border: "none", 
                outline: "none", 
                width: isListOpen ? "100%" : 60, // Shrink when showing the pill
                height: 24,
                fontSize: 13 
              }} 
            />
          </div>

          {/* <input
            value={isListOpen ? searchTerm : route}
            onFocus={() => {
              setIsListOpen(true);
              setSearchTerm(""); // Clear search when focusing to show full list
            }}
            onBlur={() => setTimeout(() => setIsListOpen(false), 200)} // Delay so click registers
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search..."
            style={{ ...styles.input, width: 120 }} 
          /> */}

          {isListOpen && (
            <div style={styles.dropdown}>
              <div 
                onMouseDown={() => {
                  onRouteChange(""); // Set route to empty string for "All"
                  setIsListOpen(false);
                  setSearchTerm("");
                }}
                style={{ ...styles.dropdownItem, fontWeight: 'regular', color: '#555' }}
              >(All routes)
              </div>
              {filteredRoutes.map((r) => {
                const { bgColor, textColor } = getRouteColors(r.route_id, 0);
                return (
                  <div 
                    key={r.route_id}
                    onMouseDown={() => { // Use onMouseDown to trigger before onBlur
                      onRouteChange(r.route_id);
                      setIsListOpen(false);
                      setSearchTerm("");
                    }}
                    style={styles.dropdownItem}
                  >
                    <span style={{ 
                      backgroundColor: bgColor, color: textColor, 
                      padding: "2px 6px", borderRadius: 4, minWidth: 20,
                      display: "inline-block", textAlign: "center"
                    }}>
                      <b>{r.route_short_name}</b>
                    </span>
                    &nbsp; {r.route_long_name}
                  </div>
                );
              })}
            </div>
          )}
        </div>
        {/* <label style={styles.label}>
          Route:&nbsp;
          <input
            value={route}
            onChange={(e) => onRouteChange(e.target.value)}
            placeholder="e.g. 704"
            style={styles.input}
          />
        </label> */}
        <label style={styles.label}>
          Direction:&nbsp;
          <select
            value={direction === null ? "all" : String(direction)}
            onChange={(e) => {
              const v = e.target.value;
              onDirectionChange(v === "all" ? null : Number(v));
            }}
            style={styles.select}
          >
            <option value="all">All</option>
            <option value="0">0 (Inbound)</option>
            <option value="1">1 (Outbound)</option>
          </select>
        </label>

        <button onClick={onRefreshNow} style={styles.button}>
          Refresh
        </button>
      </div>

      <div style={styles.right}>
        {mostRecentLocation && (
          <span style={{ ...styles.muted, marginRight: 15 }}>Most recent location: <b>{mostRecentLocation}</b></span>
        )}
        {lastUpdated ? (
          <span style={styles.muted}>Last map update: {lastUpdated}</span>
        ) : null}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  bar: {
    display: "flex",
    gap: 12,
    justifyContent: "space-between",
    alignItems: "center",
    padding: "10px 12px",
    borderBottom: "1px solid var(--border-color)",
    background: "var(--bg-nav)",
    color: "var(--text-main)",
    position: "sticky",
    top: 0,
    zIndex: 1000
  },
  left: { display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" },
  right: { display: "flex", alignItems: "center" },
  label: { display: "flex", alignItems: "center", fontSize: 14 },
  input: { padding: "6px 8px", border: "1px solid var(--border-color)", borderRadius: 6, width: 100, 
    background: "var(--bg-nav)", color: "var(--text-main)" },
  select: { padding: "6px 8px", border: "1px solid var(--border-color)", borderRadius: 6, 
    background: "var(--bg-nav)", color: "var(--text-main)" },
  button: {
    padding: "6px 10px",
    borderRadius: 6,
    border: "1px solid var(--border-color)",
    background: "var(--bg-sub-header)",
    color: "var(--text-main)",
    cursor: "pointer"
  },
  muted: { color: "var(--text-main)", opacity: 0.7, fontSize: 12 },

  dropdown: {
    position: "absolute",
    top: "100%",
    left: 45, // Adjusted to align with the start of the input
    width: 300,
    maxHeight: 300,
    overflowY: "auto",
    backgroundColor: "var(--bg-nav)",
    border: "1px solid var(--border-color)",
    borderRadius: 4,
    boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
    zIndex: 2000,
    marginTop: 4
  },
  dropdownItem: {
    padding: "8px 12px",
    cursor: "pointer",
    fontSize: 13,
    borderBottom: "1px solid var(--border-color)",
    color: "var(--text-main)",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis"
  }
};