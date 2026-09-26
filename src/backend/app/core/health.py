from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import session_factory


async def require_database_ready() -> None:
    """Require connectivity plus the migrated and seeded event table."""
    try:
        async with session_factory() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM events"))
            if result.scalar_one() < 1:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "code": "database_not_seeded",
                        "message": "Database is not seeded",
                    },
                )
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "database_unavailable",
                "message": "Database is unavailable",
            },
        ) from exc
