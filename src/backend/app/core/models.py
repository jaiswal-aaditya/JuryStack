from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base imported by Alembic and future domain models."""


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('participant', 'judge', 'organizer', 'admin')",
            name="ck_users_role",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(32), index=True)
    password_hash: Mapped[str | None] = mapped_column(String(512))

    sessions: Mapped[list[Session]] = relationship(back_populates="user")
    team_memberships: Mapped[list[TeamMember]] = relationship(back_populates="user")
    accepted_judge_invitations: Mapped[list[JudgeInvitation]] = relationship(
        back_populates="accepted_by_user"
    )
    track_eligibilities: Mapped[list[JudgeTrackEligibility]] = relationship(
        back_populates="judge"
    )
    judge_assignments: Mapped[list[JudgeAssignment]] = relationship(
        back_populates="judge"
    )
    scorecards: Mapped[list[Scorecard]] = relationship(back_populates="judge")
    audit_events: Mapped[list[AuditEvent]] = relationship(back_populates="actor")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="sessions")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    submissions_close: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    tracks: Mapped[list[Track]] = relationship(back_populates="event")
    prizes: Mapped[list[Prize]] = relationship(back_populates="event")
    teams: Mapped[list[Team]] = relationship(back_populates="event")
    projects: Mapped[list[Project]] = relationship(back_populates="event")
    custom_questions: Mapped[list[CustomQuestion]] = relationship(
        back_populates="event"
    )
    rubrics: Mapped[list[Rubric]] = relationship(back_populates="event")
    judge_invitations: Mapped[list[JudgeInvitation]] = relationship(
        back_populates="event"
    )
    audit_events: Mapped[list[AuditEvent]] = relationship(back_populates="event")


class Track(Base):
    __tablename__ = "tracks"
    __table_args__ = (UniqueConstraint("event_id", "name"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))

    event: Mapped[Event] = relationship(back_populates="tracks")
    projects: Mapped[list[Project]] = relationship(back_populates="track")
    judge_eligibilities: Mapped[list[JudgeTrackEligibility]] = relationship(
        back_populates="track"
    )


class Prize(Base):
    __tablename__ = "prizes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")

    event: Mapped[Event] = relationship(back_populates="prizes")


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (Index("ix_teams_event_name", "event_id", "name"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))

    event: Mapped[Event] = relationship(back_populates="teams")
    memberships: Mapped[list[TeamMember]] = relationship(back_populates="team")
    invites: Mapped[list[TeamInvite]] = relationship(back_populates="team")
    projects: Mapped[list[Project]] = relationship(back_populates="team")


class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (Index("ix_team_members_user_id", "user_id"),)

    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    team: Mapped[Team] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="team_memberships")


class TeamInvite(Base):
    __tablename__ = "team_invites"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    team: Mapped[Team] = relationship(back_populates="invites")


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_event_track", "event_id", "track_id"),
        Index("ix_projects_team", "team_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id"))
    title: Mapped[str] = mapped_column(String(240))
    summary: Mapped[str] = mapped_column(Text)
    repo_url: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    event: Mapped[Event] = relationship(back_populates="projects")
    team: Mapped[Team] = relationship(back_populates="projects")
    track: Mapped[Track] = relationship(back_populates="projects")
    custom_answers: Mapped[list[CustomAnswer]] = relationship(
        back_populates="project"
    )
    judge_assignments: Mapped[list[JudgeAssignment]] = relationship(
        back_populates="project"
    )
    scorecards: Mapped[list[Scorecard]] = relationship(back_populates="project")


class CustomQuestion(Base):
    __tablename__ = "custom_questions"
    __table_args__ = (UniqueConstraint("event_id", "position"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    prompt: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)
    required: Mapped[bool] = mapped_column(Boolean, default=False)

    event: Mapped[Event] = relationship(back_populates="custom_questions")
    answers: Mapped[list[CustomAnswer]] = relationship(back_populates="question")


class CustomAnswer(Base):
    __tablename__ = "custom_answers"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[str] = mapped_column(
        ForeignKey("custom_questions.id", ondelete="CASCADE"), primary_key=True
    )
    answer: Mapped[str] = mapped_column(Text)

    project: Mapped[Project] = relationship(back_populates="custom_answers")
    question: Mapped[CustomQuestion] = relationship(back_populates="answers")


class Rubric(Base):
    __tablename__ = "rubrics"
    __table_args__ = (UniqueConstraint("event_id", "version"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    event: Mapped[Event] = relationship(back_populates="rubrics")
    criteria: Mapped[list[RubricCriterion]] = relationship(back_populates="rubric")
    scorecards: Mapped[list[Scorecard]] = relationship(back_populates="rubric")


class RubricCriterion(Base):
    __tablename__ = "rubric_criteria"
    __table_args__ = (
        UniqueConstraint("rubric_id", "key"),
        CheckConstraint("weight > 0", name="ck_rubric_criteria_weight_positive"),
        CheckConstraint("minimum_score < maximum_score", name="ck_rubric_score_range"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    rubric_id: Mapped[str] = mapped_column(ForeignKey("rubrics.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(120))
    weight: Mapped[int] = mapped_column(Integer)
    minimum_score: Mapped[int] = mapped_column(Integer, default=1)
    maximum_score: Mapped[int] = mapped_column(Integer, default=5)
    position: Mapped[int] = mapped_column(Integer)

    rubric: Mapped[Rubric] = relationship(back_populates="criteria")
    scores: Mapped[list[CriterionScore]] = relationship(back_populates="criterion")


class JudgeInvitation(Base):
    __tablename__ = "judge_invitations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(320), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    accepted_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))

    event: Mapped[Event] = relationship(back_populates="judge_invitations")
    accepted_by_user: Mapped[User | None] = relationship(
        back_populates="accepted_judge_invitations"
    )


class JudgeTrackEligibility(Base):
    __tablename__ = "judge_track_eligibility"
    __table_args__ = (Index("ix_judge_track_eligibility_track_id", "track_id"),)

    judge_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    track_id: Mapped[str] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True
    )

    judge: Mapped[User] = relationship(back_populates="track_eligibilities")
    track: Mapped[Track] = relationship(back_populates="judge_eligibilities")


class JudgeAssignment(Base):
    __tablename__ = "judge_assignments"
    __table_args__ = (
        UniqueConstraint("judge_id", "project_id"),
        Index("ix_judge_assignments_project_id", "project_id"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    judge_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE")
    )

    judge: Mapped[User] = relationship(back_populates="judge_assignments")
    project: Mapped[Project] = relationship(back_populates="judge_assignments")


class Scorecard(Base):
    __tablename__ = "scorecards"
    __table_args__ = (
        UniqueConstraint("judge_id", "project_id", "rubric_id"),
        Index("ix_scorecards_judge_status", "judge_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    judge_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE")
    )
    rubric_id: Mapped[str] = mapped_column(ForeignKey("rubrics.id"))
    status: Mapped[str] = mapped_column(String(32))
    comment: Mapped[str] = mapped_column(Text, default="")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    judge: Mapped[User] = relationship(back_populates="scorecards")
    project: Mapped[Project] = relationship(back_populates="scorecards")
    rubric: Mapped[Rubric] = relationship(back_populates="scorecards")
    criterion_scores: Mapped[list[CriterionScore]] = relationship(
        back_populates="scorecard"
    )


class CriterionScore(Base):
    __tablename__ = "criterion_scores"
    __table_args__ = (
        CheckConstraint("score >= 1 AND score <= 5", name="ck_criterion_score_range"),
        Index("ix_criterion_scores_criterion_id", "criterion_id"),
    )

    scorecard_id: Mapped[str] = mapped_column(
        ForeignKey("scorecards.id", ondelete="CASCADE"), primary_key=True
    )
    criterion_id: Mapped[str] = mapped_column(
        ForeignKey("rubric_criteria.id", ondelete="CASCADE"), primary_key=True
    )
    score: Mapped[int] = mapped_column(Integer)

    scorecard: Mapped[Scorecard] = relationship(back_populates="criterion_scores")
    criterion: Mapped[RubricCriterion] = relationship(back_populates="scores")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("events.id"), index=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(120), index=True)
    detail: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    event: Mapped[Event | None] = relationship(back_populates="audit_events")
    actor: Mapped[User | None] = relationship(back_populates="audit_events")
