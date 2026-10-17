import hashlib
import json
import time

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.api.db import Base, LoginSession, Project, Revision
from apps.api.main import create_app
from apps.api.settings import Settings
from discord_bot_maker.templates import template


@pytest.fixture
def api(tmp_path):
    key = Fernet.generate_key().decode()
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'api.db'}", encryption_key=key, allow_dev_login=True, hosted_owner_id="development"))
    Base.metadata.create_all(app.state.sessions.kw["bind"])
    with TestClient(app, base_url="http://localhost:5173", headers={"Origin": "http://localhost:5173"}) as client:
        yield client, app, key


def login(client):
    assert client.post("/api/auth/dev", follow_redirects=False).status_code == 303
    me = client.get("/api/auth/me").json()
    client.headers["x-csrf-token"] = me["csrf"]


def create(client):
    response = client.post("/api/projects", json=template().model_dump(mode="json"))
    assert response.status_code == 201, response.text
    return response.json()


def test_anonymous_preview_export_and_schema(api):
    client, _, _ = api
    definition = template().model_dump(mode="json")
    assert client.get("/api/schema").json()["properties"]["schema_version"]["const"] == 1
    assert client.post("/api/validate", json=definition).status_code == 200
    preview = client.post("/api/preview", json={"definition": definition, "command": "hello", "context": {"display_name": "Jess"}})
    assert preview.status_code == 200, preview.text
    assert "Jess" in preview.json()["messages"][0]["content"]
    assert client.post("/api/export", json=definition).content.startswith(b"PK")
    assert client.get("/api/projects").status_code == 401


def test_save_conflict_csrf_and_ownership(api):
    client, app, _ = api
    login(client)
    project = create(client)
    body = {"definition": project["definition"], "version": project["version"]}
    body["definition"]["name"] = "Updated"
    assert client.put(f"/api/projects/{project['id']}", json=body).status_code == 200
    assert client.put(f"/api/projects/{project['id']}", json=body).status_code == 409
    csrf = client.headers.pop("x-csrf-token")
    assert client.post("/api/projects", json=template().model_dump(mode="json")).status_code == 403
    client.headers["x-csrf-token"] = csrf
    client.headers["origin"] = "https://evil.example"
    assert client.post("/api/projects", json=template().model_dump(mode="json")).status_code == 403
    client.headers["origin"] = "http://localhost:5173"
    with app.state.sessions.begin() as session:
        project_row = session.get(Project, project["id"])
        project_row.owner_id = "someone-else"
    for path in ("", "/events", "/revisions"):
        assert client.get(f"/api/projects/{project['id']}{path}").status_code == 404
    assert client.post(f"/api/projects/{project['id']}/stop").status_code == 404


def test_credentials_publish_rollback_and_stop(api):
    client, app, key = api
    login(client)
    project = create(client)
    path = f"/api/projects/{project['id']}"
    assert client.post(path + "/publish", json={"version": 1}).status_code == 409
    token = "secret-token-that-must-never-be-returned"
    result = client.put(path + "/credentials", json={"token": token, "application_id": "1234567"})
    assert result.status_code == 200, result.text
    with app.state.sessions() as session:
        encrypted = session.get(Project, project["id"]).encrypted_token
        assert encrypted != token
        assert Fernet(key.encode()).decrypt(encrypted.encode()).decode() == token
    first = client.post(path + "/publish", json={"version": 1}).json()["revision_id"]
    draft = template().model_dump(mode="json")
    draft["nodes"][1]["content"] = "Second version"
    assert client.put(path, json={"definition": draft, "version": 1}).status_code == 200
    second = client.post(path + "/publish", json={"version": 2}).json()["revision_id"]
    assert first != second
    assert client.post(path + "/rollback", json={"revision_id": first}).status_code == 200
    current = client.get(path).json()
    assert current["published_revision"] == first
    assert current["definition"]["nodes"][1]["content"] == "Second version"
    assert token not in client.get(path).text
    assert token not in client.get(path + "/events").text
    assert client.delete(path).status_code == 409
    assert client.post(path + "/stop").status_code == 204
    assert client.delete(path + "/credentials").status_code == 204
    assert client.delete(path).status_code == 204


def test_token_not_echoed_in_validation_errors(api):
    client, _, _ = api
    login(client)
    project = create(client)
    token = "oops"
    response = client.put(f"/api/projects/{project['id']}/credentials", json={"token": token, "application_id": "123"})
    assert response.status_code == 422
    assert token not in response.text


def test_oauth_state_and_production_config(api):
    client, _, _ = api
    assert client.get("/api/auth/callback?code=bad&state=bad").status_code == 400
    with pytest.raises(ValueError, match="Production"):
        Settings(production=True, origin="http://localhost", encryption_key="", client_id="", client_secret="")
