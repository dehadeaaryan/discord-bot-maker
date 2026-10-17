"""Project API. No Discord bot clients run in this process."""

import hashlib
import io
import json
import secrets
import time
from contextlib import asynccontextmanager
from typing import Annotated
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from discord_bot_maker import BotDefinition, Context, Engine, ExecutionError
from discord_bot_maker.definition import VARIABLES
from discord_bot_maker.export import export_archive
from discord_bot_maker.templates import template
from .db import Event, LoginSession, Project, Revision, connect
from .settings import Settings


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Preview(Input):
    definition: BotDefinition
    command: str = Field(max_length=32)
    mode: str = Field(default="slash", pattern="^(slash|prefix)$")
    context: dict = Field(default_factory=dict)


class Save(Input):
    definition: BotDefinition
    version: int = Field(ge=1)


class Credentials(Input):
    token: str = Field(min_length=20, max_length=500)
    application_id: str = Field(pattern=r"^[0-9]{1,25}$")
    guild_id: str | None = Field(default=None, pattern=r"^[0-9]{1,25}$")


class Publish(Input):
    version: int = Field(ge=1)


class Rollback(Input):
    revision_id: str


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def create_app(settings: Settings | None = None):
    settings = settings or Settings()
    engine, sessions = connect(settings.database_url)
    cipher = Fernet(settings.encryption_key.encode())

    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.dispose()

    app = FastAPI(title="Discord Bot Maker API", version="2.0.0a1", lifespan=lifespan)
    app.state.sessions, app.state.settings = sessions, settings

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        # Pydantic includes rejected input by default; never echo bot tokens.
        return JSONResponse(status_code=422, content={"detail": [{"loc": list(item["loc"]), "msg": item["msg"], "type": item["type"]} for item in error.errors()]})

    @app.middleware("http")
    async def request_limits(request, call_next):
        if request.headers.get("content-length", "0").isdigit() and int(request.headers.get("content-length", "0")) > 262144:
            return Response("Request exceeds 256 KiB", status_code=413)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if request.headers.get("origin") != settings.origin:
                return Response("Origin rejected", status_code=403)
            body = await request.body()
            if len(body) > 262144:
                return Response("Request exceeds 256 KiB", status_code=413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    def db():
        with sessions() as session:
            yield session

    DB = Annotated[Session, Depends(db)]

    def authenticated(request: Request, session: DB):
        token = request.cookies.get("dbm_session", "")
        user = session.get(LoginSession, digest(token)) if token else None
        if user is None or user.expires < time.time():
            raise HTTPException(401, "Sign in to save projects.")
        if request.method not in ("GET", "HEAD") and not secrets.compare_digest(request.headers.get("x-csrf-token", ""), user.csrf):
            raise HTTPException(403, "Session verification failed. Refresh and try again.")
        return user

    User = Annotated[LoginSession, Depends(authenticated)]

    def owned(project_id, user, session):
        project = session.get(Project, project_id)
        if project is None or project.owner_id != user.owner_id:
            raise HTTPException(404, "Project not found.")
        return project

    def host_allowed(user):
        if not settings.hosted_owner_id or user.owner_id != settings.hosted_owner_id:
            raise HTTPException(403, "Hosted bots are limited to the configured owner during the pilot. Export your bot to run it yourself.")

    def serialize(project):
        return {
            "id": project.id, "name": project.name, "version": project.version,
            "definition": json.loads(project.draft), "updated_at": project.updated_at,
            "has_token": bool(project.encrypted_token), "application_id": project.application_id,
            "guild_id": project.guild_id, "published_revision": project.published_revision,
            "desired_state": project.desired_state,
            "observed_state": project.observed_state if project.lease_until > time.time() or project.desired_state == "stopped" else "waiting for runner",
        }

    def sign_in(owner_id, username):
        token = secrets.token_urlsafe(48)
        with sessions.begin() as session:
            session.execute(delete(LoginSession).where(LoginSession.expires < time.time()))
            session.add(LoginSession(id=digest(token), owner_id=owner_id, username=username, csrf=secrets.token_urlsafe(32), expires=time.time() + 604800))
        response = RedirectResponse("/builder", status_code=303)
        response.set_cookie("dbm_session", token, max_age=604800, httponly=True, secure=settings.production, samesite="lax", path="/")
        response.delete_cookie("dbm_oauth", path="/")
        return response

    @app.get("/api/health")
    def health(session: DB):
        session.execute(select(1))
        return {"status": "ok"}

    @app.get("/api/config")
    def config():
        return {"oauth_enabled": bool(settings.client_id and settings.client_secret), "dev_login": settings.allow_dev_login, "variables": sorted(VARIABLES)}

    @app.get("/api/schema")
    def schema():
        return BotDefinition.model_json_schema()

    @app.get("/api/templates")
    def templates():
        return {name: template(name).model_dump(mode="json") for name in ("greeting", "rules", "faq")}

    @app.post("/api/preview")
    def preview(body: Preview):
        try:
            context = Context(**body.context)
            if len(json.dumps(body.context)) > 10000:
                raise ValueError("Preview context is too large.")
            return Engine(body.definition).execute(body.command, context, body.mode)
        except (ValueError, TypeError) as error:
            raise HTTPException(422, str(error)) from None

    @app.post("/api/validate")
    def validate(definition: BotDefinition):
        return {"definition": definition.model_dump(mode="json")}

    @app.post("/api/export")
    def export(definition: BotDefinition):
        return StreamingResponse(io.BytesIO(export_archive(definition)), media_type="application/zip", headers={"Content-Disposition": 'attachment; filename="discord-bot.zip"'})

    @app.get("/api/auth/login")
    def login():
        if not settings.client_id or not settings.client_secret:
            raise HTTPException(503, "Discord sign-in has not been configured.")
        state = secrets.token_urlsafe(32)
        response = RedirectResponse("https://discord.com/oauth2/authorize?" + urlencode({
            "client_id": settings.client_id, "response_type": "code", "scope": "identify",
            "redirect_uri": settings.redirect_uri, "state": state,
        }))
        response.set_cookie("dbm_oauth", cipher.encrypt(state.encode()).decode(), max_age=600, httponly=True, secure=settings.production, samesite="lax", path="/")
        return response

    @app.get("/api/auth/callback")
    async def callback(request: Request, code: str = "", state: str = ""):
        try:
            expected = cipher.decrypt(request.cookies.get("dbm_oauth", "").encode(), ttl=600).decode()
            if not state or not secrets.compare_digest(expected, state) or not code:
                raise InvalidToken
        except (InvalidToken, ValueError):
            raise HTTPException(400, "Sign-in expired. Please try again.") from None
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                response = await client.post("https://discord.com/api/oauth2/token", data={"client_id": settings.client_id, "client_secret": settings.client_secret, "grant_type": "authorization_code", "code": code, "redirect_uri": settings.redirect_uri})
                response.raise_for_status()
                profile = await client.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {response.json()['access_token']}"})
                profile.raise_for_status()
                user = profile.json()
                return sign_in(str(user["id"]), user["username"])
            except (httpx.HTTPError, KeyError, ValueError):
                raise HTTPException(502, "Discord sign-in failed. Try again.") from None

    @app.post("/api/auth/dev")
    def development_login():
        if not settings.allow_dev_login or settings.production:
            raise HTTPException(404)
        return sign_in("development", "Local developer")

    @app.get("/api/auth/me")
    def me(user: User):
        return {"id": user.owner_id, "name": user.username, "csrf": user.csrf, "can_host": bool(settings.hosted_owner_id and user.owner_id == settings.hosted_owner_id)}

    @app.post("/api/auth/logout")
    def logout(user: User, session: DB):
        session.delete(user)
        session.commit()
        response = Response(status_code=204)
        response.delete_cookie("dbm_session", path="/")
        return response

    @app.get("/api/projects")
    def list_projects(user: User, session: DB):
        return [serialize(project) for project in session.scalars(select(Project).where(Project.owner_id == user.owner_id).order_by(Project.updated_at.desc()))]

    @app.post("/api/projects", status_code=201)
    def create_project(definition: BotDefinition, user: User, session: DB):
        if session.scalar(select(func.count()).select_from(Project).where(Project.owner_id == user.owner_id)) >= 100:
            raise HTTPException(409, "Project limit reached.")
        project = Project(owner_id=user.owner_id, name=definition.name, draft=definition.model_dump_json())
        session.add(project)
        session.commit()
        return serialize(project)

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str, user: User, session: DB):
        return serialize(owned(project_id, user, session))

    @app.put("/api/projects/{project_id}")
    def save_project(project_id: str, body: Save, user: User, session: DB):
        owned(project_id, user, session)
        changed = session.execute(update(Project).where(Project.id == project_id, Project.version == body.version).values(draft=body.definition.model_dump_json(), name=body.definition.name, version=Project.version + 1, updated_at=time.time()))
        if changed.rowcount != 1:
            session.rollback()
            raise HTTPException(409, "This project changed in another tab. Reopen it before saving.")
        session.commit()
        session.expire_all()
        return serialize(owned(project_id, user, session))

    @app.delete("/api/projects/{project_id}", status_code=204)
    def delete_project(project_id: str, user: User, session: DB):
        project = owned(project_id, user, session)
        if project.desired_state != "stopped" or project.lease_until > time.time():
            raise HTTPException(409, "Stop the bot and wait for its runner to disconnect before deleting it.")
        session.execute(delete(Event).where(Event.project_id == project_id))
        session.execute(delete(Revision).where(Revision.project_id == project_id))
        session.delete(project)
        session.commit()

    @app.put("/api/projects/{project_id}/credentials")
    def credentials(project_id: str, body: Credentials, user: User, session: DB):
        host_allowed(user)
        project = owned(project_id, user, session)
        if session.scalar(select(Project.id).where(Project.application_id == body.application_id, Project.id != project_id)):
            raise HTTPException(409, "This Discord application is already connected to another project.")
        project.encrypted_token = cipher.encrypt(body.token.encode()).decode()
        project.application_id, project.guild_id = body.application_id, body.guild_id
        project.credential_version += 1
        project.synced_revision = None
        session.add(Event(project_id=project.id, message="Bot credentials updated."))
        session.commit()
        return {"has_token": True}

    @app.delete("/api/projects/{project_id}/credentials", status_code=204)
    def remove_credentials(project_id: str, user: User, session: DB):
        project = owned(project_id, user, session)
        project.desired_state, project.encrypted_token = "stopped", None
        project.credential_version += 1
        session.commit()

    @app.post("/api/projects/{project_id}/publish")
    def publish(project_id: str, body: Publish, user: User, session: DB):
        host_allowed(user)
        # Serialize pilot quota checks across API workers using the owner's session row.
        session.execute(select(LoginSession).where(LoginSession.owner_id == user.owner_id).with_for_update())
        project = owned(project_id, user, session)
        if project.version != body.version:
            raise HTTPException(409, "Save the latest draft before publishing.")
        if not project.encrypted_token:
            raise HTTPException(409, "Connect your bot credentials first.")
        count = session.scalar(select(func.count()).select_from(Project).where(Project.desired_state == "running", Project.id != project.id))
        if count >= settings.max_bots:
            raise HTTPException(409, "Hosted bot limit reached.")
        definition = BotDefinition.model_validate_json(project.draft)
        revision = Revision(project_id=project.id, definition=definition.model_dump_json())
        session.add(revision)
        session.flush()
        project.published_revision, project.desired_state = revision.id, "running"
        session.add(Event(project_id=project.id, message="Published a new version."))
        session.commit()
        return {"revision_id": revision.id}

    @app.post("/api/projects/{project_id}/stop", status_code=204)
    def stop(project_id: str, user: User, session: DB):
        project = owned(project_id, user, session)
        project.desired_state = "stopped"
        session.add(Event(project_id=project.id, message="Stop requested."))
        session.commit()

    @app.get("/api/projects/{project_id}/revisions")
    def revisions(project_id: str, user: User, session: DB):
        owned(project_id, user, session)
        return [{"id": row.id, "created_at": row.created_at} for row in session.scalars(select(Revision).where(Revision.project_id == project_id).order_by(Revision.created_at.desc()).limit(50))]

    @app.post("/api/projects/{project_id}/rollback")
    def rollback(project_id: str, body: Rollback, user: User, session: DB):
        host_allowed(user)
        project = owned(project_id, user, session)
        revision = session.get(Revision, body.revision_id)
        if not revision or revision.project_id != project.id:
            raise HTTPException(404, "Published version not found.")
        # Rollback selects a published version; it does not restart a stopped bot or overwrite its draft.
        project.published_revision = revision.id
        session.add(Event(project_id=project.id, message="Selected an earlier published version."))
        session.commit()
        return {"revision_id": revision.id}

    @app.get("/api/projects/{project_id}/events")
    def events(project_id: str, user: User, session: DB):
        owned(project_id, user, session)
        return [{"message": event.message, "created_at": event.created_at} for event in session.scalars(select(Event).where(Event.project_id == project_id).order_by(Event.created_at.desc()).limit(50))]

    return app


app = create_app()
