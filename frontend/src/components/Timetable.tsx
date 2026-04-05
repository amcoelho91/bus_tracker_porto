import React, { useMemo } from "react";
import { type TimetableResponse } from "../api/client";

interface Props {
  data: TimetableResponse;
}

export function Timetable({ data }: Props) {
  const { columns, rows, tripData } = useMemo(() => {
    // 1. Create a map of Stop ID -> Stop Name for the headers
    const stopNamesMap: Record<string, string> = {};
    data.reference_stops.forEach(s => {
      stopNamesMap[s.stop_id] = s.stop_name;
    });
    const sortedColumns = data.reference_stops.map((s) => ({ id: s.stop_id, name: s.stop_name }));

    // 2. Group trip data by trip_id for O(1) lookup during rendering
    const tripsMap: Record<string, Record<string, string>> = {};
    
    data.trips.forEach((item) => {
      if (!tripsMap[item.trip_id]) {
        tripsMap[item.trip_id] = {};
      }
      // Strip seconds for a cleaner look (HH:MM:SS -> HH:MM)
      tripsMap[item.trip_id][item.stop_id] = item.arrival_time.slice(0, 5);
    });

    // 3. Create the rows (Array of Trip IDs)
    // Note: The backend already sorted these trips chronologically
    const sortedTripIds = Array.from(new Set(data.trips.map(d => d.trip_id)));

    return { columns: sortedColumns, rows: sortedTripIds, tripData: tripsMap };
  }, [data]);

  if (!data.trips || data.trips.length === 0) return null;

  return (
    <div style={{ 
      overflowX: "auto", 
      maxHeight: "500px", 
      border: "1px solid var(--border-color)",
      borderRadius: "8px",
      background: "var(--bg-main)" 
    }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
        <thead style={{ position: "sticky", top: 0, background: "var(--bg-sub-header)", zIndex: 1 }}>
          <tr>
            <th style={{ ...headerStyle, position: "sticky", top: 0, left: 0, zIndex: 10 }}>Trip ID</th>
            {columns.map((col) => (
              <th key={col.id} style={{ 
                ...headerStyle, width: '128px', minWidth: '128px', maxWidth: '128px',
                padding: "10px 0" // Remove horizontal padding to prevent "offset" math
              }}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%' }}>
                  <div style={{ fontSize: '10px', color: '#666', marginBottom: '4px', width: '100%', textAlign: 'center' }}>
                    {col.id}
                  </div>

                  <div style={{ width: '120px', whiteSpace: 'normal', wordWrap: 'break-word',
                    lineHeight: '1.2', textAlign: 'center',fontWeight: 'bold' }}>
                    {col.name}
                  </div>
                </div>
              </th>
            ))}
            {/* <th style={headerStyle}>Trip ID</th>
            {columns.map((col) => (
              <th key={col.id} style={headerStyle}>
                <div style={{ fontSize: "10px", color: "#666" }}>{col.id}</div>
                <div style={{ width: "128px", whiteSpace: "normal", textOverflow: "ellipsis", textAlign: "center"}}>
                  {col.name}
                </div>
              </th>
            ))} */}
          </tr>
        </thead>
        <tbody>
          {rows.map((tripId) => (
            <tr key={tripId} style={{ borderBottom: "1px solid var(--border-color)" }}>
              <td style={{ ...cellStyle, fontWeight: "bold", background: "var(--bg-sub-header)", 
                position: "sticky", left: 0 }}>
                {tripId.split("_").pop()} {/* Shorten Trip ID for display */}
              </td>
              {columns.map((col) => {
                const time = tripData[tripId][col.id];
                return (
                  <td key={col.id} style={{ ...cellStyle, textAlign: "center" }}>
                    {time || <span style={{ color: "#888888" }}>—</span>}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const headerStyle: React.CSSProperties = {
  padding: "10px",
  borderBottom: "2px solid var(--border-color)",
  color: "var(--text-main)",
  background: "var(--bg-sub-header)",
  whiteSpace: "nowrap",
  textAlign: "center",
  verticalAlign: "bottom"
};

const cellStyle: React.CSSProperties = {
  padding: "8px",
  color: "var(--text-main)",
  whiteSpace: "nowrap", 
  width: "128px",
  minWidth: "128px",
  maxWidth: "128px"
};