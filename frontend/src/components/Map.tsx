import "leaflet/dist/leaflet.css";
import React, { useMemo } from "react";
import { MapContainer, TileLayer, Popup, Polyline, CircleMarker } from "react-leaflet";
import type { VehicleLatest } from "../api/client";

type Props = {
  vehicles: VehicleLatest[];
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

        return (
          <React.Fragment key={v.vehicle_id}>
            {prevPos ? (
              <>
                <CircleMarker
                  center={prevPos}
                  radius={7}
                  pathOptions={{ color: "red" }}
                >
                  <Popup>
                    <div style={{ fontSize: 13 }}>
                      <div><b>PREVIOUS</b></div>
                      <div><b>Route:</b> {v.route_id ?? "-"}</div>
                      <div><b>Vehicle:</b> {label}</div>
                      <div><b>Direction:</b> {v.direction ?? "-"}</div>
                      <div><b>Trip:</b> {v.trip_id ?? "-"}</div>
                      <div><b>Observed:</b> {v.prev_observed_at ? new Date(v.prev_observed_at).toLocaleString() : "-"}</div>
                      <div><b>Lat,Lon:</b> {prevPos[0]}, {prevPos[1]}</div>
                    </div>
                  </Popup>
                </CircleMarker>

                <Polyline positions={[prevPos, curPos]} pathOptions={{ color: "gray" }} />
              </>
            ) : null}

            <CircleMarker
              center={curPos}
              radius={8}
              pathOptions={{ color: "green" }}
            >
              <Popup>
                <div style={{ fontSize: 13 }}>
                  <div><b>CURRENT</b></div>
                  <div><b>Route:</b> {v.route_id ?? "-"}</div>
                  <div><b>Vehicle:</b> {label}</div>
                  <div><b>Direction:</b> {v.direction ?? "-"}</div>
                  <div><b>Trip:</b> {v.trip_id ?? "-"}</div>
                  <div><b>Speed:</b> {v.speed ?? "-"} </div>
                  <div><b>Observed:</b> {new Date(v.observed_at).toLocaleString()}</div>
                  <div><b>Lat,Lon:</b> {curPos[0]}, {curPos[1]}</div>
                </div>
              </Popup>
            </CircleMarker>
          </React.Fragment>
        );
      })}
    </MapContainer>
  );
}