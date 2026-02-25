export type VehicleLatest = {
  fleet_vehicle_id: string | null;
  vehicle_id: string;
  route_id: string | null;
  direction: number | null;
  trip_id: string | null;
  speed: number | null;
  bearing: number | null;
  heading: number | null;
  observed_at: string;
  lon: number;
  lat: number;

  prev_observed_at: string | null;
  prev_lon: number | null;
  prev_lat: number | null;
};

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function fetchLatest(routeId?: string, direction?: number | null): Promise<VehicleLatest[]> {
  const url = new URL(`${API_BASE}/api/latest`);
  if (routeId && routeId.trim().length > 0) url.searchParams.set("route", routeId.trim());
  if (direction === 0 || direction === 1) url.searchParams.set("direction", String(direction));

  // cache buster to force a new response every time
  url.searchParams.set("_ts", String(Date.now()));

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch latest: ${res.status}`);
  return res.json();
}