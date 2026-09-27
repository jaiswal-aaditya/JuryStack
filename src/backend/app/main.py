from fastapi import Depends, FastAPI

from app.auth.routes import router as auth_router
from app.core.config import settings
from app.core.errors import ApiError, api_error_handler
from app.core.health import require_database_ready

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_exception_handler(ApiError, api_error_handler)
app.include_router(auth_router)


@app.get("/api/health", tags=["system"])
async def health(_: None = Depends(require_database_ready)) -> dict[str, str]:
    """Report readiness only when the migrated, seeded database responds."""
    return {"status": "ok", "database": "ready"}
