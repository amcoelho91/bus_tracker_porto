from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.health import router as health_router
from app.api.routes import router as routes_router
from app.api.schedules import router as schedules_router
from app.api.shapes import router as shapes_router
from app.api.stops import router as stops_router
from app.api.stoptimes_planned import router as stoptimes_planned_router
from app.api.trips import router as trips_router
from app.api.vehicles import router as vehicles_router
from app.api.history import router as history_router

app = FastAPI(title="Bus Tracker API", version="0.1.0")

origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def no_cache_api(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

app.include_router(health_router, prefix="/api")
app.include_router(history_router, prefix="/api", tags=["History"])
app.include_router(routes_router, prefix="/api", tags=["Routes"])
app.include_router(schedules_router, prefix="/api", tags=["Schedules"])
app.include_router(shapes_router, prefix="/api", tags=["Shapes"])
app.include_router(stops_router, prefix="/api", tags=["Stops"])
app.include_router(stoptimes_planned_router, prefix="/api", tags=["Planned Stop Times"])
app.include_router(trips_router, prefix="/api", tags=["Trips"])
app.include_router(vehicles_router, prefix="/api", tags=["Vehicles"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)