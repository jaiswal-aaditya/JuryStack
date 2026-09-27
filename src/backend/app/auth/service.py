import asyncio
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from app.auth.security import (
    DUMMY_PASSWORD_HASH,
    hash_session_token,
    new_session_token,
    verify_password,
)
from app.core.errors import AuthenticationRequired
from app.core.models import AuditEvent, Session, User


class AuthStore(Protocol):
    async def user_by_email(self, email: str) -> User | None: ...

    async def user_by_session_hash(
        self, token_hash: str, now: datetime
    ) -> User | None: ...

    async def delete_session(self, token_hash: str) -> None: ...

    async def add_session(self, session: Session) -> None: ...

    async def add_audit_event(self, event: AuditEvent) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


@dataclass(frozen=True)
class LoginResult:
    user: User
    token: str
    expires_at: datetime


class AuthService:
    def __init__(
        self,
        store: AuthStore,
        session_ttl_seconds: int,
        *,
        offload_password_verification: bool = True,
        password_verifier: Callable[[str, str], bool] = verify_password,
    ) -> None:
        self.store = store
        self.session_ttl_seconds = session_ttl_seconds
        self.offload_password_verification = offload_password_verification
        self.password_verifier = password_verifier

    async def login(
        self, email: str, password: str, current_token: str | None = None
    ) -> LoginResult:
        user = await self.store.user_by_email(email.strip().casefold())
        encoded_hash = (
            user.password_hash if user and user.password_hash else DUMMY_PASSWORD_HASH
        )
        if self.offload_password_verification:
            password_matches = await asyncio.to_thread(
                self.password_verifier, password, encoded_hash
            )
        else:
            password_matches = self.password_verifier(password, encoded_hash)
        if not password_matches or not user or not user.password_hash:
            raise AuthenticationRequired("Invalid email or password.")

        token = new_session_token()
        expires_at = datetime.now(UTC) + timedelta(seconds=self.session_ttl_seconds)
        session = Session(
            id=f"ses_{secrets.token_hex(16)}",
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=expires_at,
        )
        try:
            if current_token:
                await self.store.delete_session(hash_session_token(current_token))
            await self.store.add_session(session)
            await self.store.add_audit_event(
                AuditEvent(
                    id=f"audit_auth_login_{secrets.token_hex(16)}",
                    event_id=None,
                    actor_id=user.id,
                    action="auth.login",
                    detail="{}",
                )
            )
            await self.store.commit()
        except Exception:
            await self.store.rollback()
            raise
        return LoginResult(user=user, token=token, expires_at=expires_at)

    async def current_user(self, token: str | None) -> User | None:
        if not token:
            return None
        return await self.store.user_by_session_hash(
            hash_session_token(token), datetime.now(UTC)
        )

    async def logout(self, token: str, actor_id: str) -> None:
        try:
            await self.store.delete_session(hash_session_token(token))
            await self.store.add_audit_event(
                AuditEvent(
                    id=f"audit_auth_logout_{secrets.token_hex(16)}",
                    event_id=None,
                    actor_id=actor_id,
                    action="auth.logout",
                    detail="{}",
                )
            )
            await self.store.commit()
        except Exception:
            await self.store.rollback()
            raise
