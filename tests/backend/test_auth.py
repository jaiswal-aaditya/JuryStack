from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

import httpx
import pytest
from fastapi import Depends, FastAPI

from app.auth.dependencies import get_auth_service, require_roles
from app.auth.policies import require_owned_resource
from app.auth.roles import Role
from app.auth.routes import router as auth_router
from app.auth.security import hash_password, hash_session_token, verify_password
from app.auth.service import AuthService
from app.core.errors import ApiError, api_error_handler
from app.core.models import AuditEvent, Session, User

DEMO_PASSWORD = "correct horse battery staple"
JudgeActor = Annotated[User, Depends(require_roles(Role.JUDGE))]
OrganizerActor = Annotated[
    User, Depends(require_roles(Role.ORGANIZER, Role.ADMIN))
]
OwnerActor = Annotated[User, Depends(require_owned_resource())]


def auth_service(store: MemoryAuthStore) -> AuthService:
    return AuthService(store, 3600, offload_password_verification=False)


class MemoryAuthStore:
    def __init__(self, users: list[User]) -> None:
        self.users = {user.email: user for user in users}
        self.sessions: dict[str, tuple[User, datetime]] = {}
        self.audit_events: list[AuditEvent] = []

    async def user_by_email(self, email: str) -> User | None:
        return self.users.get(email)

    async def user_by_session_hash(
        self, token_hash: str, now: datetime
    ) -> User | None:
        record = self.sessions.get(token_hash)
        if record is None or record[1] <= now:
            return None
        return record[0]

    async def delete_session(self, token_hash: str) -> None:
        self.sessions.pop(token_hash, None)

    async def add_session(self, session: Session) -> None:
        user = next(user for user in self.users.values() if user.id == session.user_id)
        self.sessions[session.token_hash] = (user, session.expires_at)

    async def add_audit_event(self, event: AuditEvent) -> None:
        self.audit_events.append(event)

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def make_user(user_id: str, email: str, role: Role) -> User:
    return User(
        id=user_id,
        email=email,
        display_name=email.partition("@")[0],
        role=role,
        password_hash=hash_password(DEMO_PASSWORD),
    )


def build_test_app(service: AuthService) -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(auth_router)

    async def override_auth_service() -> AuthService:
        return service

    app.dependency_overrides[get_auth_service] = override_auth_service

    @app.get("/judge-only")
    async def judge_only(_: JudgeActor) -> dict[str, bool]:
        return {"allowed": True}

    @app.get("/organizer-only")
    async def organizer_only(_: OrganizerActor) -> dict[str, bool]:
        return {"allowed": True}

    @app.get("/owned/{owner_user_id}")
    async def owned(_: OwnerActor) -> dict[str, bool]:
        return {"allowed": True}

    return app


def client_for(service: AuthService) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=build_test_app(service)),
        base_url="http://test",
    )


@pytest.mark.asyncio
async def test_missing_and_invalid_sessions_return_401() -> None:
    participant = make_user("usr_participant", "person@example.test", Role.PARTICIPANT)
    service = auth_service(MemoryAuthStore([participant]))

    async with client_for(service) as client:
        missing = await client.get("/api/auth/me")
        client.cookies.set("session", "not-a-session")
        invalid = await client.get("/api/auth/me")

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert missing.json()["error"]["code"] == "authentication_required"


@pytest.mark.asyncio
async def test_login_rejects_role_escalation_and_sets_opaque_cookie() -> None:
    participant = make_user("usr_participant", "person@example.test", Role.PARTICIPANT)
    service = auth_service(MemoryAuthStore([participant]))

    async with client_for(service) as client:
        escalation = await client.post(
            "/api/auth/login",
            json={
                "email": participant.email,
                "password": DEMO_PASSWORD,
                "role": "admin",
            },
        )
        response = await client.post(
            "/api/auth/login",
            json={"email": participant.email, "password": DEMO_PASSWORD},
        )
        current = await client.get("/api/auth/me")

    assert escalation.status_code == 422
    assert response.status_code == 200
    assert response.json()["role"] == "participant"
    assert current.json()["id"] == participant.id
    set_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert participant.password_hash not in response.text
    assert DEMO_PASSWORD not in response.text


@pytest.mark.asyncio
async def test_login_rotates_session_and_logout_invalidates_it() -> None:
    participant = make_user("usr_participant", "person@example.test", Role.PARTICIPANT)
    store = MemoryAuthStore([participant])
    old_token = "old-opaque-token"
    store.sessions[hash_session_token(old_token)] = (
        participant,
        datetime.now(UTC) + timedelta(hours=1),
    )
    service = auth_service(store)

    async with client_for(service) as client:
        client.cookies.set("session", old_token, domain="test.local", path="/")
        login = await client.post(
            "/api/auth/login",
            json={"email": participant.email, "password": DEMO_PASSWORD},
        )
        rotated_token = client.cookies["session"]
        assert rotated_token != old_token
        assert hash_session_token(old_token) not in store.sessions

        logout = await client.post("/api/auth/logout")
        client.cookies.set("session", rotated_token, domain="test.local", path="/")
        after_logout = await client.get("/api/auth/me")

    assert login.status_code == 200
    assert logout.status_code == 204
    assert after_logout.status_code == 401
    assert hash_session_token(rotated_token) not in store.sessions
    assert [event.action for event in store.audit_events] == [
        "auth.login",
        "auth.logout",
    ]


@pytest.mark.asyncio
async def test_participant_cannot_access_judge_route() -> None:
    participant = make_user("usr_participant", "person@example.test", Role.PARTICIPANT)
    store = MemoryAuthStore([participant])
    token = "participant-token"
    store.sessions[hash_session_token(token)] = (
        participant,
        datetime.now(UTC) + timedelta(hours=1),
    )

    async with client_for(auth_service(store)) as client:
        client.cookies.set("session", token, domain="test.local", path="/")
        response = await client.get("/judge-only")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_judge_cannot_access_organizer_route() -> None:
    judge = make_user("jdg_test", "judge@example.test", Role.JUDGE)
    store = MemoryAuthStore([judge])
    token = "judge-token"
    store.sessions[hash_session_token(token)] = (
        judge,
        datetime.now(UTC) + timedelta(hours=1),
    )

    async with client_for(auth_service(store)) as client:
        client.cookies.set("session", token, domain="test.local", path="/")
        response = await client.get("/organizer-only")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_user_cannot_access_another_users_owned_resource() -> None:
    participant = make_user("usr_one", "one@example.test", Role.PARTICIPANT)
    store = MemoryAuthStore([participant])
    token = "owner-token"
    store.sessions[hash_session_token(token)] = (
        participant,
        datetime.now(UTC) + timedelta(hours=1),
    )

    async with client_for(auth_service(store)) as client:
        client.cookies.set("session", token, domain="test.local", path="/")
        response = await client.get("/owned/usr_two")

    assert response.status_code == 403


def test_password_hashes_use_argon2id() -> None:
    encoded = hash_password(DEMO_PASSWORD)

    assert encoded.startswith("$argon2id$")
    assert verify_password(DEMO_PASSWORD, encoded)
    assert not verify_password("incorrect password", encoded)
