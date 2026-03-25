from pydantic import BaseModel
from datetime import datetime

class VehicleLatest(BaseModel):
    fleet_vehicle_id: str | None
    vehicle_id: str
    route_id: str | None
    direction: int | None
    trip_id: str | None
    speed: float | None
    bearing: int | None
    heading: int | None

    observed_at: datetime
    lon: float
    lat: float
    last_stop_id: str | None
    last_stop_name: str | None

    # previous position (may be null if no history exists)
    prev_observed_at: datetime | None = None
    prev_lon: float | None = None
    prev_lat: float | None = None
    prev_heading: int | None = None