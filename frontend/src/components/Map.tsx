import "leaflet/dist/leaflet.css";
import React, { useMemo } from "react";
import L from 'leaflet'; // pedropt10 - Import Leaflet for custom icons
import { MapContainer, TileLayer, Popup, Polyline, CircleMarker, Marker } from "react-leaflet";
import type { VehicleLatest } from "../api/client";

type Props = {
  vehicles: VehicleLatest[];
};

// pedropt10
const getRouteColors = (routeId: string | null, direction: number | string | null) => {
  // Translate "direction" to 0 or 1 index
  const sIdx = direction === 0 ? 0 : 1;

  const r = routeId ? parseInt(routeId) : null;

  let bgColor = '#000000';
  let textColor = '#FFFFFF';

  // Logic for Background Color
  if (r === null) {
    bgColor = sIdx === 0 ? '#555555' : '#000000';
  } else if (r >= 1 && r <= 99) {
    bgColor = '#AB803D';
  } else if (r >= 100 && r <= 499) {
    bgColor = sIdx === 0 ? '#06579E' : '#268FFF';
  } else if (r >= 500 && r <= 599) {
    bgColor = sIdx === 0 ? '#b39b00' : '#E1C403';
    textColor = sIdx === 0 ? '#FFFFFF' : '#000000';
  } else if (r >= 600 && r <= 699) {
    bgColor = sIdx === 0 ? '#00800B' : '#00C911';
  } else if (r >= 700 && r <= 799) {
    bgColor = sIdx === 0 ? '#B00000' : '#FF0000';
  } else if (r >= 800 && r <= 899) {
    bgColor = sIdx === 0 ? '#7302A7' : '#B51AFD';
  } else if (r >= 900 && r <= 999) {
    bgColor = sIdx === 0 ? '#B05601' : '#F28118';
  } else {
    bgColor = sIdx === 0 ? '#000000' : '#555555';
  }

  return { bgColor, textColor };
};

export function Map({ vehicles }: Props) {
  const center = useMemo<[number, number]>(() => {
    if (!vehicles.length) return [41.1579, -8.6291]; // Porto fallback
    const avgLat = vehicles.reduce((s, v) => s + v.lat, 0) / vehicles.length;
    const avgLon = vehicles.reduce((s, v) => s + v.lon, 0) / vehicles.length;
    return [avgLat, avgLon];
  }, [vehicles]);

  return (
    <MapContainer center={center} zoom={13} style={{ height: "calc(100vh - 92px)", width: "100%" }}>
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {vehicles.map((v) => {
        const label = v.fleet_vehicle_id ?? v.vehicle_id;
        const hasPrev =
          v.prev_lat !== null &&
          v.prev_lon !== null &&
          (v.prev_lat !== v.lat || v.prev_lon !== v.lon);

        const prevPos: [number, number] | null = hasPrev ? [v.prev_lat as number, v.prev_lon as number] : null;
        const curPos: [number, number] = [v.lat, v.lon];

        // pedropt10 - Get colors based on route and direction
        const { bgColor, textColor } = getRouteColors(v.route_id, v.direction);

        const heading = v.heading ?? 0;
        let BusMarkerRotation = 0;
        let flexDir: "column" | "row" | "column-reverse" | "row-reverse" = "column";
        let arrowRotation = 0;
        let marginStyle = "0px"; // Default margin for arrow

        // Your quadrant logic:
        if (heading >= 315 || heading < 45) { // North (NW to NE)
          BusMarkerRotation = heading;
          flexDir = "column";         // Arrow on TOP
          arrowRotation = 0;
        } else if (heading >= 45 && heading < 135) { // East (NE to SE)
          BusMarkerRotation = heading - 90;
          flexDir = "row-reverse";    // Arrow on RIGHT
          arrowRotation = 90;
          marginStyle = "0 0 0 -1px"; // Pulls it 3px closer from the Right
        } else if (heading >= 135 && heading < 225) { // South (SE to SW)
          BusMarkerRotation = heading - 180;
          flexDir = "column-reverse"; // Arrow on BOTTOM
          arrowRotation = 180;
        } else { // West (SW to NW)
          BusMarkerRotation = heading - 270;
          flexDir = "row";            // Arrow on LEFT
          arrowRotation = 270;
          marginStyle = "0 -1px 0 0"; // Pulls it 3px closer from the Left
        }

        // pedropt10 - Create a custom divIcon for the bus marker
        // external div: element rotation
        // 1st internal div: triangle pointer (arrow-like)
        // 2nd internal div: label with route_id
        // filter: drop-shadow(0px 0.5px 0px black) drop-shadow(0px -0.5px 0px black) drop-shadow(0.5px 0px 0px black) drop-shadow(-0.5px 0px 0px black);
        const busIcon = L.divIcon({
          className: 'custom-bus-marker',
          html: `
            <div style="
              display: flex;
              flex-direction: ${flexDir};
              align-items: center;
              justify-content: center;
              transform: rotate(${BusMarkerRotation}deg);
            ">
              <div style="
                width: 0; height: 0; 
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-bottom: 9px solid ${bgColor};
                transform: rotate(${arrowRotation}deg);
                margin: ${marginStyle};
                filter: drop-shadow(0 0 0.3px black) drop-shadow(0 0 0.3px black);
                transform-origin: center;
              "></div>
              
              <div style="
                background-color: ${bgColor};
                color: ${textColor};
                padding: 2px 5px;
                border-radius: 3px;
                border: 1px solid black;
                font-weight: bold;
                font-size: 11px;
                z-index: 2;
              ">
                ${v.route_id ?? '??'}
              </div>
            </div>
          `,
          iconSize: [30, 30],
          iconAnchor: [15, 15]
        });

        return (
          <React.Fragment key={v.vehicle_id}>
            {prevPos ? (
              <>
                {/* <CircleMarker
                  center={prevPos}
                  radius={7}
                  pathOptions={{ color: "red" }}
                > */}
                <Marker 
                  position={v.lat && v.lon ? [v.lat, v.lon] : prevPos} 
                  icon={busIcon}
                >
                  <Popup>
                    <div style={{ fontSize: 13 }}>
                      <div><b>PREVIOUS</b></div>
                      <div><b>Route:</b> {v.route_id ?? "-"}</div>
                      <div><b>Vehicle:</b> {label}</div>
                      <div><b>Direction:</b> {v.direction ?? "-"}</div>
                      {/* <div><b>Trip:</b> {v.trip_id ?? "-"}</div> */}
                      <div><b>Observed:</b> {v.prev_observed_at ? new Date(v.prev_observed_at).toLocaleString() : "-"}</div>
                      {/* <div><b>Lat,Lon:</b> {prevPos[0]}, {prevPos[1]}</div> */}
                    </div>
                  </Popup>
                </Marker>
                {/* </CircleMarker> */}

                <Polyline positions={[prevPos, curPos]} pathOptions={{ color: "gray" }} />
              </>
            ) : null}

            {/* <CircleMarker
              center={curPos}
              radius={8}
              pathOptions={{ color: "green" }}
            > */}
            <Marker 
              position={v.lat && v.lon ? [v.lat, v.lon] : curPos} 
              icon={busIcon}
            >
              <Popup>
                <div style={{ fontSize: 13 }}>
                  <div><b>CURRENT</b></div>
                  <div><b>Route:</b> {v.route_id ?? "-"}</div>
                  <div><b>Vehicle:</b> {label}</div>
                  <div><b>Direction:</b> {v.direction ?? "-"}</div>
                  <div><b>Trip:</b> {v.trip_id ?? "-"}</div>
                  {/* <div><b>Speed:</b> {v.speed ?? "-"} </div> */}
                  <div><b>Observed:</b> {new Date(v.observed_at).toLocaleString()}</div>
                  {/* <div><b>Lat,Lon:</b> {curPos[0]}, {curPos[1]}</div> */}
                </div>
              </Popup>
            </Marker>
            {/* </CircleMarker> */}
          </React.Fragment>
        );
      })}
    </MapContainer>
  );
}