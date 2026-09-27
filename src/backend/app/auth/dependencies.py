from collections.abc import AsyncIterator, Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.repository import AuthRepository
from app.auth.roles import Role
from app.auth.service import AuthService
from app.core.config import settings
from app.core.database import get_database_session
from app.core.errors import AuthenticationRequired, PermissionDenied
from app.core.models import User


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AuthService:
    return AuthService(AuthRepository(session), settings.session_ttl_seconds)


async def get_optional_actor(
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User | None:
    return await service.current_user(request.cookies.get(settings.session_cookie_name))


async def get_current_actor(
    actor: Annotated[User | None, Depends(get_optional_actor)],
) -> User:
    if actor is None:
        raise AuthenticationRequired()
    return actor


def require_roles(*allowed_roles: Role) -> Callable[..., AsyncIterator[User]]:
    allowed = frozenset(allowed_roles)

    async def dependency(
        actor: Annotated[User, Depends(get_current_actor)],
    ) -> User:
        if Role(actor.role) not in allowed:
            raise PermissionDenied()
        return actor

    return dependency


CurrentActor = Annotated[User, Depends(get_current_actor)]
