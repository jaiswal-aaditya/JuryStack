from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import AuditEvent, Session, User


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def user_by_email(self, email: str) -> User | None:
        return await self.session.scalar(select(User).where(User.email == email))

    async def user_by_session_hash(
        self, token_hash: str, now: datetime
    ) -> User | None:
        return await self.session.scalar(
            select(User)
            .join(Session, Session.user_id == User.id)
            .where(Session.token_hash == token_hash, Session.expires_at > now)
        )

    async def delete_session(self, token_hash: str) -> None:
        await self.session.execute(
            delete(Session).where(Session.token_hash == token_hash)
        )

    async def add_session(self, session: Session) -> None:
        self.session.add(session)

    async def add_audit_event(self, event: AuditEvent) -> None:
        self.session.add(event)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
