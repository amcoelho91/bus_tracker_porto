import "leaflet/dist/leaflet.css";
import React, { useMemo, useEffect } from "react";
import L from 'leaflet';
import { MapContainer, TileLayer, Popup, Polyline, CircleMarker, useMap, Pane } from "react-leaflet";
import type { VehicleLatest, RouteShape } from "../api/client";
// Reuse your existing color logic
import { getRouteColors, getDirectionDestination } from "./Map"; 

type Props = {
  vehicles: VehicleLatest[];
  shapeData: RouteShape | null;
  selectedRoute: string;
};

/**
 * Component to handle auto-fitting the map bounds to the historical path
 */
function FitBounds({ positions }: { positions: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    if (positions.length > 0) {
      const bounds = L.latLngBounds(positions);
      map.fitBounds(bounds, { padding: [30, 30], animate: true });
    }
  }, [positions, map]);
  return null;
}

export function HistoryMap({ vehicles, shapeData, selectedRoute }: Props) {
  // 1. Calculate historical positions for the polyline
  const historyPositions = useMemo<[number, number][]>(
    () => vehicles.map((v) => [v.lat, v.lon]),
    [vehicles]
  );

  // 2. Reuse the styling logic from Map.tsx
  // We default to direction 1 for the general route color theme
  const { bgColor, textColor, hasShadow } = useMemo(
    () => getRouteColors(selectedRoute, 1),
    [selectedRoute]
  );

  return (
    <MapContainer
      center={[41.1579, -8.6291]}
      zoom={13}
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* Reusing your Pane structure for consistent layering */}
      <Pane name="history-shape-pane" style={{ zIndex: 390 }} />
      <Pane name="history-path-pane" style={{ zIndex: 400 }} />
      <Pane name="history-pings-pane" style={{ zIndex: 450 }} />
      <Pane name="popup-pane" style={{ zIndex: 700 }} />

      {/* I. STATIC ROUTE SHAPE (Context) */}
      {shapeData && shapeData.coordinates.length > 0 && (
        <Polyline
          positions={shapeData.coordinates}
          pathOptions={{
            color: "#666",
            weight: 3,
            opacity: 0.3,
            dashArray: "5, 10",
            pane: "history-shape-pane",
          }}
        />
      )}

      {/* II. HISTORICAL BREADCRUMB LINE */}
      {historyPositions.length > 1 && (
        <>
          {/* Shadow effect if the route type usually has one */}
          {hasShadow && (
            <Polyline
              positions={historyPositions}
              pathOptions={{
                color: "#000",
                weight: 7,
                opacity: 0.2,
                pane: "history-path-pane",
              }}
            />
          )}
          <Polyline
            positions={historyPositions}
            pathOptions={{
              color: bgColor,
              weight: 4,
              opacity: 0.8,
              lineJoin: "round",
              pane: "history-path-pane",
            }}
          />
        </>
      )}

      {/* III. INDIVIDUAL GPS PINGS (The Dots) */}
      {vehicles.map((v, idx) => {
        const timeStr = new Date(v.observed_at).toLocaleTimeString("pt-PT", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });
        const v_label = v.vehicle_id;

        return (
          <CircleMarker
            key={`${v.observed_at}-${idx}`}
            center={[v.lat, v.lon]}
            radius={idx === vehicles.length - 1 ? 7 : 4} // Make the "last" known point bigger
            pane="history-pings-pane"
            pathOptions={{
              color: idx === vehicles.length - 1 ? "#000" : "white",
              fillColor: bgColor,
              fillOpacity: 1,
              weight: 1.5,
            }}
          >
            <Popup pane="popup-pane">
              <div style={{ fontSize: "13px", minWidth: "140px" }}>
                <div style={{ marginBottom: "5px", borderBottom: "1px solid #eee", paddingBottom: "3px" }}>
                   <strong>Historical Ping</strong>
                </div>
                
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
                   <span style={{ 
                      backgroundColor: bgColor, color: textColor, 
                      padding: "2px 6px", borderRadius: 4, fontWeight: "bold" 
                   }}>
                     {v.route_id}
                   </span>
                   <span style={{ fontSize: "11px", color: "#666" }}>{timeStr}</span>
                </div>

                <div style={{ fontSize: "12px" }}>
                  <div>🚌 <b>Vehicle:</b> {v_label}</div>
                  <div>🆔 <b>Trip:</b> {v.trip_id ?? "N/A"}</div>
                  {v.last_stop_id && (
                    <div style={{ marginTop: "4px", color: "#444" }}>
                      🚏 <b>Near:</b> {v.last_stop_id}
                    </div>
                  )}
                </div>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}

      {/* IV. AUTO-FOCUS LOGIC */}
      <FitBounds positions={historyPositions} />
    </MapContainer>
  );
}