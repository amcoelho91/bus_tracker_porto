from fastapi import APIRouter

router = APIRouter(tags=["stats"])

# Later endpoints, e.g.
# GET /api/stats/travel-time?route=704&dow=1&hour=8