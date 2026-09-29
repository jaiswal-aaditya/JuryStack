from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError

from app.audit.routes import router as audit_router
from app.auth.routes import router as auth_router
from app.core.config import settings
from app.core.errors import (
    ApiError,
    api_error_handler,
    request_validation_error_handler,
)
from app.core.health import require_database_ready
from app.events.routes import router as events_router
from app.judging.routes import router as judging_router
from app.projects.routes import router as projects_router
from app.results.routes import router as results_router
from app.teams.routes import router as teams_router
from app.voting.routes import router as voting_router

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, request_validation_error_handler)
app.include_router(auth_router)
app.include_router(events_router)
app.include_router(judging_router)
app.include_router(teams_router)
app.include_router(voting_router)
app.include_router(projects_router)
app.include_router(results_router)
app.include_router(audit_router)


@app.get("/api/health", tags=["system"])
async def health(_: None = Depends(require_database_ready)) -> dict[str, str]:
    """Report readiness only when the migrated, seeded database responds."""
    return {"status": "ok", "database": "ready"}
