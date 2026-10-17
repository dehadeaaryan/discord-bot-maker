"""Persistence shared by the API and runner; schema managed by Alembic."""

import time
import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def uid():
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class LoginSession(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(80))
    username: Mapped[str] = mapped_column(String(100))
    csrf: Mapped[str] = mapped_column(String(100))
    expires: Mapped[float] = mapped_column(Float)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(80))
    draft: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time)
    encrypted_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    application_id: Mapped[str | None] = mapped_column(String(25), nullable=True, unique=True)
    guild_id: Mapped[str | None] = mapped_column(String(25), nullable=True)
    credential_version: Mapped[int] = mapped_column(Integer, default=0)
    published_revision: Mapped[str | None] = mapped_column(String(36), nullable=True)
    synced_revision: Mapped[str | None] = mapped_column(String(36), nullable=True)
    desired_state: Mapped[str] = mapped_column(String(20), default="stopped")
    observed_state: Mapped[str] = mapped_column(String(30), default="stopped")
    lease_owner: Mapped[str | None] = mapped_column(String(36), nullable=True)
    lease_until: Mapped[float] = mapped_column(Float, default=0)


class Revision(Base):
    __tablename__ = "revisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    definition: Mapped[str] = mapped_column(Text)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    message: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


def connect(url):
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {"pool_pre_ping": True}
    engine = create_engine(url, **kwargs)
    return engine, sessionmaker(engine, expire_on_commit=False)
