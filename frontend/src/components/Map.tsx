import "leaflet/dist/leaflet.css";
import React, { useMemo, useEffect, useState } from "react";
import L from 'leaflet'; // pedropt10 - Import Leaflet for custom icons
import { MapContainer, TileLayer, Popup, Polyline, CircleMarker, Marker, Pane } from "react-leaflet";
import type { VehicleLatest, RouteShape, Stop } from "../api/client";

type Props = {
  vehicles: VehicleLatest[];
  shapeData0: RouteShape | null;
  shapeData1?: RouteShape | null; // optional second shape for "All" direction
  selectedRoute: string;
  selectedDirection: number | null;
  stops: Stop[]; 
};

// pedropt10
export const getRouteColors = (routeId: string | null, direction: number | string | null) => {
  // If direction is 0 OR null, use index 0. 
  const d = (direction === 1 || direction === "1") ? 1 : 0;
  const isNightRoute = !routeId || routeId.toUpperCase().includes("M");
  const r = routeId ? parseInt(routeId) : null;

  let bgColor = '#000000';
  let textColor = '#FFFFFF';
  let hasShadow = false;

  // // Logic for Background Color
  if (isNightRoute) {
    bgColor = d === 0 ? '#000000' : '#555555'; 
  } else if (r !== null && r >= 1 && r <= 99) {
    bgColor = '#AB803D';
  } else if (r !== null && r >= 100 && r <= 499) {
    bgColor = d === 0 ? '#268FFF' : '#06579E'; 
  } else if (r !== null && r >= 500 && r <= 599) {
    bgColor = d === 0 ? '#E1C403' : '#b39b00'; 
    textColor = d === 0 ? '#000000' : '#FFFFFF'; 
    if (d === 0) hasShadow = true;
  } else if (r !== null && r >= 600 && r <= 699) {
    bgColor = d === 0 ? '#00C911' : '#00800B'; 
  } else if (r !== null && r >= 700 && r <= 799) {
    bgColor = d === 0 ? '#FF0000' : '#B00000'; 
  } else if (r !== null && r >= 800 && r <= 899) {
    bgColor = d === 0 ? '#B51AFD' : '#7302A7'; 
  } else if (r !== null && r >= 900 && r <= 999) {
    bgColor = d === 0 ? '#F28118' : '#B05601'; 
    if (d === 0) hasShadow = true; 
  } else {
    bgColor = d === 0 ? '#555555' : '#000000'; 
  }

  return { bgColor, textColor, hasShadow };
};

// pedropt10 - added shapeData0 prop to receive route shapes from MapPage
export function Map({ vehicles, shapeData0, shapeData1, selectedRoute, selectedDirection, stops }: Props) {
  // Colors for primary shape (Direction 0 or currently selected)
  const primaryColors = useMemo(() => 
    getRouteColors(selectedRoute, selectedDirection === null ? 0 : selectedDirection), 
    [selectedRoute, selectedDirection]
  );

  // Colors for secondary shape (Direction 1)
  const secondaryColors = useMemo(() => 
    getRouteColors(selectedRoute, 1), 
    [selectedRoute]
  );

  const center = useMemo<[number, number]>(() => {
    if (shapeData0 && shapeData0.coordinates.length > 0) {
      // Use the middle point of the shape to center the map
      const midIdx = Math.floor(shapeData0.coordinates.length / 2);
      return shapeData0.coordinates[midIdx];
    }
    if (!vehicles.length) return [41.1579, -8.6291]; // Porto fallback
    const avgLat = vehicles.reduce((s, v) => s + v.lat, 0) / vehicles.length;
    const avgLon = vehicles.reduce((s, v) => s + v.lon, 0) / vehicles.length;
    return [avgLat, avgLon];
  }, [vehicles, shapeData0]);

  const mapRef = React.useRef<L.Map | null>(null);

  useEffect(() => {
    // We only want to add the control once the map is initialized
    if (!mapRef.current) return;
    const map = mapRef.current;

    const LocateControl = L.Control.extend({
      onAdd: function() {
        // Create a standard Leaflet button container
        const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
        const button = L.DomUtil.create('a', '', container);
        
        button.innerHTML = '📍';
        button.title = "My Location";
        button.href = "#";
        button.style.fontSize = '24px';
        button.style.width = '44px';   
        button.style.height = '44px';
        button.style.display = 'flex';
        button.style.alignItems = 'center';
        button.style.justifyContent = 'center';
        button.style.backgroundColor = 'white';
        button.style.color = 'black';
        button.style.fontWeight = 'bold';

        button.onclick = function(e) {
          e.preventDefault();
          e.stopPropagation();
          // Leaflet's built-in locate method
          map.locate({ setView: false, enableHighAccuracy: true});
        };

        return container;
      }
    });

    const control = new LocateControl({ position: 'topright' });
    control.addTo(map);

    // Marker to indicate where the user is found
    map.on('locationfound', (e) => {
      map.flyTo(e.latlng, 16, { animate: true, duration: 1.5 });
      L.circleMarker(e.latlng, { radius: 8, fillColor: '#268FFF', fillOpacity: 0.9,
         color: '#FFFFFF', weight: 3, opacity: 1 }).addTo(map);
    });

    map.on('locationerror', () => alert("Location access denied."));

    return () => {
      control.remove();
    };
  }, [mapRef]);

  return (
    <MapContainer ref={mapRef} center={center} zoom={13} style={{ height: "100%", width: "100%" }}>
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      
      {/* Secondary Shape - Z-index 390 keeps it below Primary */}
      <Pane name="secondary-pane" style={{ zIndex: 390 }}>
        {shapeData1 && shapeData1.coordinates && shapeData1.coordinates.length > 0 && (
          <>
            {secondaryColors.hasShadow && (
             <Polyline
              key={`shadow-sec-${selectedRoute}`}
              positions={shapeData1.coordinates}
              pathOptions={{ color: "#000", weight: 6, opacity: 0.3, lineJoin: "round", lineCap: "round", pane: "secondary-pane" }} />)}
            <Polyline 
              key={`path-sec-${selectedRoute}`}
              positions={shapeData1.coordinates}
              pathOptions={{ color: secondaryColors.bgColor, weight: 4, opacity: 1.0, lineJoin: "round", lineCap: "round", pane: "secondary-pane" }} />
          </>
        )}
      </Pane>

      {/* Primary Shape - Z-index 400 keeps it above Secondary */}
      <Pane name="dominant-pane" style={{ zIndex: 400 }}>
        {shapeData0 && shapeData0.coordinates && shapeData0.coordinates.length > 0 && (
          <>
            {primaryColors.hasShadow && (
             <Polyline
              key={`shadow-dom-${selectedRoute}`}
              positions={shapeData0.coordinates}
              pathOptions={{ color: "#000", weight: 8, opacity: 0.3, lineJoin: "round", lineCap: "round", pane: "dominant-pane" }} />)}
            <Polyline 
              key={`path-dom-${selectedRoute}`}
              positions={shapeData0.coordinates}
              pathOptions={{ color: primaryColors.bgColor, weight: 5, opacity: 1.0, lineJoin: "round", lineCap: "round", pane: "dominant-pane" }} />
          </>
        )}
      </Pane>

      {/* Render the Stops */}
      <Pane name="stops-pane" style={{ zIndex: 600 }}>
        {stops.map((stop: Stop) => (
          <CircleMarker
            key={stop.stop_id}
            center={[stop.lat, stop.lon]}
            radius={5}
            pathOptions={{
              color: "#333",
              fillColor: "#fff",
              fillOpacity: 1,
              weight: 2
            }}
          >
            <Popup>
              <div style={{ fontSize: "14px" }}>
                <div style={{ marginBottom: "5px" }}>
                  <strong>{stop.stop_name}</strong>
                </div>
                <div style={{ color: "#666", fontSize: "12px", marginBottom: "8px" }}>
                  ID: {stop.stop_id}
                </div>
                {stop.stop_url && (
                  <a 
                    href={stop.stop_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    style={{ 
                      color: "#187EC2", 
                      textDecoration: "none", 
                      fontWeight: "bold",
                      display: "block",
                      borderTop: "1px solid #eee",
                      paddingTop: "5px"
                    }}
                  >
                    View Timetables →
                  </a>
                )}
              </div>
            </Popup>
          </CircleMarker>
      ))}</Pane>

      {/* Render the Vehicles' markers with route info*/}
      {vehicles.map((v) => {
        const label = v.fleet_vehicle_id ?? v.vehicle_id;
        const hasPrev =
          v.prev_lat !== null &&
          v.prev_lon !== null &&
          (v.prev_lat !== v.lat || v.prev_lon !== v.lon);

        const prevPos: [number, number] | null = hasPrev ? [v.prev_lat as number, v.prev_lon as number] : null;
        const curPos: [number, number] = [v.lat, v.lon];

        // pedropt10 - Determine if the observation is older than 2 minutes
        // useMemo ensures this calculation only runs when observed_at changes, improving performance
        const obsTime = new Date(v.observed_at).getTime();
        const now = Date.now();
        const isOld = (now - obsTime) > (2 * 60 * 1000); // 2 minutes

        // pedropt10 - Get colors based on route and direction
        const { bgColor: routeBg, textColor: routeText, hasShadow } = getRouteColors(v.route_id, v.direction);

        // Override colors if observation is older than 2 minutes, otherwise use route colors
        const bgColor = isOld ? '#a3a3a3' : routeBg;
        const textColor = isOld ? '#FFFFFF' : routeText;

        const heading = v.heading ?? 0;
        let BusMarkerRotation = 0;
        let flexDir: "column" | "row" | "column-reverse" | "row-reverse" = "column";
        let arrowRotation = 0;
        let marginStyle = "0px"; // Default margin for arrow

        // Quadrant logic:
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
              font-family: inherit;
              font-weight: 700;
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
                font-family: inherit;
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
                <CircleMarker
                        center={prevPos}
                        radius={5}
                        pathOptions={{ 
                          fillColor: bgColor, fillOpacity: 1, color: "#000000", weight: 1 
                        }}
                >
                  <Popup>
                    <div style={{ fontSize: 13 }}>
                      <div><b>Location: PREVIOUS</b></div>
                      <div><b>Route:</b> {v.route_id ?? "-"}</div>
                      <div><b>Vehicle:</b> {label}</div>
                      <div><b>Direction:</b> {v.direction ?? "-"}</div>
                      <div><b>Observed:</b> {v.prev_observed_at ? new Date(v.prev_observed_at).toLocaleTimeString('pt-PT', { 
                        hour: '2-digit', 
                        minute: '2-digit', 
                        second: '2-digit' 
                      }) : "-"}</div>
                      {/* <div><b>Trip:</b> {v.trip_id ?? "-"}</div> */}
                      {/* <div><b>Lat,Lon:</b> {prevPos[0]}, {prevPos[1]}</div> */}
                    </div>
                  </Popup>
                </CircleMarker>
                {/* </CircleMarker> */}

                {/*<Polyline
                  positions={[prevPos, curPos]}
                  pathOptions={{ color: "gray", weight: 2, dashArray: '5, 5' }} 
                /> */}
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
                  {/* <div><b>CURRENT</b></div> */}
                  <div><b>Location: {isOld ? "🔴 DELAYED" : "🟢 CURRENT"}</b></div>
                  <div><b>Route:</b> {v.route_id ?? "-"}</div>
                  <div><b>Vehicle:</b> {label}</div>
                  <div><b>Direction:</b> {v.direction ?? "-"}</div>
                  <div><b>Trip:</b> {v.trip_id ?? "-"}</div>
                  {/* <div><b>Speed:</b> {v.speed ?? "-"} </div> */}
                  <div><b>Observed:</b> {new Date(v.observed_at).toLocaleTimeString('pt-PT', { 
                          hour: '2-digit', 
                          minute: '2-digit', 
                          second: '2-digit' 
                        })}</div>
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