from fastapi import APIRouter

from app.api.v1.routes import (
    agents,
    alerts,
    auth,
    health,
    incidents,
    ingestion,
    investigations,
    realtime,
    reports,
    roles,
    search,
    settings,
    threat_intel,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(health.router, tags=["health"])
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(ingestion.router)
api_router.include_router(alerts.router)
api_router.include_router(incidents.router)
api_router.include_router(investigations.router)
api_router.include_router(realtime.router)
api_router.include_router(threat_intel.router)
api_router.include_router(agents.router)
api_router.include_router(reports.router)
api_router.include_router(search.router)
api_router.include_router(settings.router)
