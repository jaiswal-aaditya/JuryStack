from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/api/health", tags=["system"])
async def health() -> dict[str, str]:
    """Report process health without exercising product behavior."""
    return {"status": "ok"}
