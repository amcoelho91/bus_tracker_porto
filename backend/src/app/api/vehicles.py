from fastapi import APIRouter, Query, HTTPException
from app.services.vehicles import get_latest_by_route_and_direction, get_latest_by_fleet_id
from app.models.vehicles import VehicleLatest

router = APIRouter(tags=["vehicles"])

@router.get("/latest", response_model=list[VehicleLatest])
def latest(
    route: str | None = Query(default=None, description="Route id, e.g. 704"),
    direction: int | None = Query(default=None, description="Direction id, 0 or 1"),
):
    return get_latest_by_route_and_direction(route, direction)

@router.get("/vehicle/{vehicle_id}", response_model=VehicleLatest)
def vehicle_latest(vehicle_id: str):
    row = get_latest_by_fleet_id(vehicle_id)
    if not row:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return row