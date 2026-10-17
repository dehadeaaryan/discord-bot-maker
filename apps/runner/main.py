"""Owner-pilot supervisor. Atomic database leases fence concurrent runners."""

import json
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

from cryptography.fernet import Fernet
from sqlalchemy import or_, select, update

from apps.api.db import Event, Project, Revision, connect
from apps.api.settings import Settings

LEASE_SECONDS = 30


def claim(session, project_id, owner, now):
    result = session.execute(update(Project).where(
        Project.id == project_id, Project.desired_state == "running",
        or_(Project.lease_until < now, Project.lease_owner == owner),
    ).values(lease_owner=owner, lease_until=now + LEASE_SECONDS))
    session.commit()
    return result.rowcount == 1


def terminate(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main():
    settings = Settings()
    if not settings.hosting_enabled or not settings.hosted_owner_id:
        raise SystemExit("Configure ENABLE_HOSTING=1 and HOSTED_OWNER_ID before starting the pilot runner.")
    if not __import__("os").getenv("ENCRYPTION_KEY"):
        raise SystemExit("Configure the same ENCRYPTION_KEY as the API.")
    _, sessions = connect(settings.database_url)
    cipher, owner = Fernet(settings.encryption_key.encode()), str(uuid.uuid4())
    running, retries = {}, {}
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        while not stopping:
            started = time.monotonic()
            try:
                with sessions() as session:
                    candidates = list(session.scalars(select(Project).where(Project.owner_id == settings.hosted_owner_id, Project.desired_state == "running")))
                    desired = {project.id: project for project in candidates}
                    for project_id, (process, revision, credentials) in list(running.items()):
                        project = desired.get(project_id)
                        changed = not project or project.published_revision != revision or project.credential_version != credentials
                        if changed or process.poll() is not None:
                            terminate(process)
                            running.pop(project_id)
                            if project and not changed:
                                failures = retries.get(project_id, (0, 0))[1] + 1
                                retries[project_id] = (time.time() + min(300, 2 ** min(failures, 8)), failures)
                            session.execute(update(Project).where(Project.id == project_id, Project.lease_owner == owner).values(lease_owner=None, lease_until=0, observed_state="retrying" if project else "stopped"))
                            session.add(Event(project_id=project_id, message="Bot restarting after a change or disconnect." if project else "Bot stopped."))
                            session.commit()
                    for project in candidates:
                        now = time.time()
                        if retries.get(project.id, (0, 0))[0] > now:
                            continue
                        if project.id not in running and len(running) >= settings.max_bots:
                            continue
                        if not claim(session, project.id, owner, now):
                            if project.id in running:
                                terminate(running.pop(project.id)[0])
                            continue
                        if project.id in running:
                            continue
                        revision = session.get(Revision, project.published_revision)
                        if not revision or not project.encrypted_token:
                            continue
                        process = subprocess.Popen([sys.executable, "-m", "apps.runner.bot"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
                        try:
                            process.stdin.write(json.dumps({
                                "definition": json.loads(revision.definition), "token": cipher.decrypt(project.encrypted_token.encode()).decode(),
                                "sync": project.synced_revision != revision.id, "guild_id": project.guild_id,
                                "project_id": project.id, "revision_id": revision.id, "lease_owner": owner,
                            }))
                            process.stdin.close()
                        except Exception:
                            terminate(process)
                            raise
                        running[project.id] = (process, revision.id, project.credential_version)
                        session.execute(update(Project).where(Project.id == project.id, Project.lease_owner == owner).values(observed_state="connecting"))
                        session.add(Event(project_id=project.id, message="Runner connecting to Discord."))
                        session.commit()
                Path("/tmp/discord-bot-maker-runner-heartbeat").write_text(str(time.time()))
            except Exception:
                # A runner that cannot renew its lease must disconnect immediately.
                for process, _, _ in running.values():
                    terminate(process)
                running.clear()
                print("Runner could not refresh state; clients disconnected. Retrying.", flush=True)
            delay = max(0, 3 - (time.monotonic() - started))
            end = time.monotonic() + delay
            while not stopping and time.monotonic() < end:
                time.sleep(0.1)
    finally:
        for process, _, _ in running.values():
            terminate(process)
        with sessions.begin() as session:
            session.execute(update(Project).where(Project.lease_owner == owner).values(lease_owner=None, lease_until=0, observed_state="stopped"))


if __name__ == "__main__":
    main()
