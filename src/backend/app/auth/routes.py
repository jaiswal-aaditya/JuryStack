from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.auth.dependencies import CurrentActor, get_auth_service
from app.auth.schemas import CurrentUserResponse, LoginRequest
from app.auth.service import AuthService
from app.core.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=CurrentUserResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> CurrentUserResponse:
    result = await service.login(
        payload.email, payload.password.get_secret_value(),
        request.cookies.get(settings.session_cookie_name),
    )
    response.set_cookie(
        key=settings.session_cookie_name,
        value=result.token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_seconds,
        expires=result.expires_at,
        path="/",
    )
    return CurrentUserResponse.model_validate(result.user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    actor: CurrentActor,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    token = request.cookies[settings.session_cookie_name]
    await service.logout(token, actor.id)
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )


@router.get("/me", response_model=CurrentUserResponse)
async def current_user(actor: CurrentActor) -> CurrentUserResponse:
    return CurrentUserResponse.model_validate(actor)
