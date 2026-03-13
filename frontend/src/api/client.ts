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

export type Stop = {
  stop_id: string;
  stop_name: string;
  lat: number;
  lon: number;
  zone_id: string;
  stop_url: string;
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

export type RouteShape = {
  coordinates: [number, number][];
  color: string;
};

export async function fetchRouteShape(routeId: string, directionId: number | null): Promise<RouteShape | null> {
  if (!routeId || directionId === null) return null;
  
  const url = new URL(`${API_BASE}/api/shapes`);
  url.searchParams.set("route_id", routeId.trim());
  url.searchParams.set("direction_id", String(directionId));

  try {
    const res = await fetch(url.toString(), { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch (err) {
    console.error("Error fetching route shape:", err);
    return null;
  }
}

export interface AllRoutes {
  route_id: string;
  route_short_name: string;
  route_long_name: string;
}

export async function fetchAllRoutes(): Promise<any[]> {
  const url = new URL(`${API_BASE}/api/routes`);

  try {
    const res = await fetch(url.toString(), { cache: "no-store" });
    if (!res.ok) {
      console.warn("Fetch routes returned non-OK status:", res.status);
      return [];
    }
    return await res.json();
  } catch (err) {
    console.error("Error fetching all routes:", err);
    return [];
  }
}

export async function fetchStops(routeId: string, directionId: number | null): Promise<Stop[]> {
  if (!routeId || directionId === null) return [];

  const url = new URL(`${API_BASE}/api/stops`);
  url.searchParams.set("route_id", routeId.trim());
  url.searchParams.set("direction_id", String(directionId));

  try {
    const res = await fetch(url.toString(), { cache: "no-store" });
    if (!res.ok) throw new Error(`Failed to fetch stops: ${res.status}`);
    return res.json();
  } catch (err) {
    console.error("Error fetching stops:", err);
    return [];
  }
}