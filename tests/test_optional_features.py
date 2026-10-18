import asyncio
import io
import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from discord_bot_maker import Bot, CommandContext, Settings, Simulator, UserError, configure_logging


def test_settings_migration_is_atomic_and_server_scoped(tmp_path):
    bot = Bot("offline", slash_only=True, storage=tmp_path / "bot.sqlite3")
    first = Settings(1, {"greeting": "Hello"})
    bot.settings(10, first).update(greeting="Hi")
    def migrate(values):
        return {"welcome": values.pop("greeting")}
    second = Settings(2, {"welcome": "Hello", "enabled": True}, migrations={1: migrate})
    assert bot.settings(10, second).get() == {"welcome": "Hi", "enabled": True}
    assert bot.settings(11, second).get()["welcome"] == "Hello"
    with pytest.raises(ValueError, match="newer"):
        bot.settings(10, first).get()
    with pytest.raises(ValueError, match="Invalid type"):
        bot.settings(10, second).update(enabled="yes")
    assert bot.settings(10, second).get()["enabled"] is True
    bad = Settings(3, {"welcome": "Hello"}, migrations={2: lambda values: {"unknown": 1}})
    with pytest.raises(ValueError, match="Unknown"):
        bot.settings(10, bad).get()
    assert bot.settings(10, second).get()["welcome"] == "Hi"
    bot.store.close()


@pytest.mark.asyncio
async def test_jobs_retry_cancel_recover_and_persist(tmp_path):
    path = tmp_path / "jobs.sqlite3"
    bot = Bot("offline", slash_only=True, storage=path)
    attempts = []
    @bot.job("deliver")
    async def deliver(payload):
        attempts.append(payload)
        if len(attempts) == 1:
            raise RuntimeError("secret")
    bot.jobs._clock = lambda: 100
    job_id = bot.jobs.schedule("deliver", payload={"id": 1}, retries=1)
    assert await bot.jobs.run_pending()
    assert bot.jobs.status(job_id) == {"status": "pending", "attempts": 1}
    assert not await bot.jobs.run_pending()
    bot.jobs._clock = lambda: 103
    assert await bot.jobs.run_pending()
    assert bot.jobs.status(job_id) == {"status": "done", "attempts": 2}
    cancelled = bot.jobs.schedule("deliver")
    assert bot.jobs.cancel(cancelled)
    assert not bot.jobs.cancel(cancelled)
    restart = bot.jobs.schedule("deliver")
    with bot.store._database.transaction() as connection:
        connection.execute("UPDATE dbm_jobs SET status='running' WHERE id=?", (restart,))
    await bot.client.close()
    restored = Bot("offline", slash_only=True, storage=path)
    restored.job("deliver")(deliver)
    restored.jobs._clock = lambda: 104
    restored.jobs.recover()
    assert await restored.jobs.run_pending()
    assert restored.jobs.status(restart)["status"] == "done"
    assert restored.jobs.status(cancelled)["status"] == "cancelled"
    await restored.client.close()


@pytest.mark.asyncio
async def test_running_job_cancel_is_cooperative():
    bot = Bot("offline", slash_only=True, storage=":memory:")
    started = asyncio.Event()
    @bot.job("wait")
    async def wait(payload):
        started.set()
        await asyncio.Event().wait()
    job_id = bot.jobs.schedule("wait")
    runner = asyncio.create_task(bot.jobs.run_pending())
    await started.wait()
    assert bot.jobs.cancel(job_id)
    await runner
    assert bot.jobs.status(job_id)["status"] == "cancelled"
    await bot.client.close()


@pytest.mark.asyncio
async def test_trigger_event_and_auto_role():
    bot = Bot("offline", slash_only=True, storage=":memory:")
    bot.trigger("hello", "Hi {{user.display_name}}", exact=True)
    sim = Simulator(bot)
    interaction, result = sim.interaction()
    message = SimpleNamespace(author=interaction.user, channel=interaction.channel, guild=interaction.guild, content="HELLO")
    await sim.event("message", message)
    assert result.content == "Hi Sam"
    message.author.bot = True
    await sim.event("message", message)
    assert len(result.messages) == 1
    role = SimpleNamespace(id=99, managed=False, is_default=lambda: False)
    # A role object implements hierarchy comparison in discord.py.
    class Role:
        def __ge__(self, other):
            return False
        managed = False
        def is_default(self):
            return False
    role = Role()
    member = SimpleNamespace(guild=SimpleNamespace(get_role=lambda id: role, me=SimpleNamespace(guild_permissions=SimpleNamespace(manage_roles=True), top_role=100)), add_roles=AsyncMock())
    bot.auto_role(99)
    await bot.emit("member_join", member)
    member.add_roles.assert_awaited_once()
    await sim.close()
    await bot.client.close()


@pytest.mark.asyncio
async def test_moderation_confirmation_rechecks_and_audits():
    bot = Bot("offline", slash_only=True, storage=":memory:")
    sim = Simulator(bot)
    interaction, result = sim.interaction(permissions=("kick_members",))
    actor = interaction.user
    actor.top_role = 10
    me = SimpleNamespace(id=3, top_role=20, guild_permissions=SimpleNamespace(kick_members=True))
    guild = interaction.guild
    guild.me, guild.owner_id = me, 999
    member = SimpleNamespace(id=2, guild=guild, top_role=5, kick=AsyncMock())
    async def fetch(id):
        return {1: actor, 2: member, 3: me}[id]
    guild.fetch_member = fetch
    prompt = bot.moderation.kick(CommandContext(bot, interaction), member, reason="Spam")
    # Invoke actual confirmation actions with a shared realistic server fixture.
    click = CommandContext(bot, interaction)
    assert "completed" in await prompt.buttons[0].reply(click)
    member.kick.assert_awaited_once()
    assert bot.moderation.audit(10)[0]["status"] == "completed"
    assert not bot.moderation.audit(11)
    with pytest.raises(UserError, match="already"):
        await prompt.buttons[0].reply(click)
    prompt = bot.moderation.kick(click, member, reason="Spam")
    member.top_role = 30
    with pytest.raises(UserError, match="below"):
        await prompt.buttons[0].reply(click)
    assert member.kick.await_count == 1
    await sim.close()
    await bot.client.close()


def test_structured_logging():
    stream = io.StringIO()
    logger = configure_logging(stream=stream)
    logger.info("Ready")
    record = json.loads(stream.getvalue())
    assert record["message"] == "Ready"
    assert record["level"] == "INFO"
    logger.handlers.clear()
    logger.propagate = True


def test_scaffold_is_complete_and_does_not_overwrite(tmp_path):
    from discord_bot_maker.scaffold import scaffold
    directory = tmp_path / "bot"
    files = scaffold(directory)
    assert {"Dockerfile", "compose.yaml", "bot.py", "requirements.txt"} <= set(files)
    compile((directory / "bot.py").read_text(), "bot.py", "exec")
    (directory / "bot.py").write_text("keep me")
    with pytest.raises(ValueError, match="overwrite"):
        scaffold(directory)
    assert (directory / "bot.py").read_text() == "keep me"


@pytest.mark.asyncio
async def test_health_responses_and_managed_shutdown(monkeypatch):
    from discord_bot_maker.operations import health_server
    bot = Bot("offline", slash_only=True, storage=":memory:")
    captured = {}
    class Server:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def serve_forever(self):
            return
    async def start(handler, host, port, **kwargs):
        captured["handler"] = handler
        return Server()
    monkeypatch.setattr(asyncio, "start_server", start)
    await health_server(bot, "127.0.0.1", 8080)
    async def request(line):
        writer = SimpleNamespace(write=lambda data: captured.update(response=data), drain=AsyncMock(), close=lambda: None, wait_closed=AsyncMock())
        await captured["handler"](SimpleNamespace(readline=AsyncMock(return_value=line)), writer)
        return captured["response"]
    assert b"503" in await request(b"GET /health HTTP/1.1\r\n")
    monkeypatch.setattr(bot.client, "is_ready", lambda: True)
    assert b"200" in await request(b"GET /health HTTP/1.1\r\n")
    assert b"404" in await request(b"GET / HTTP/1.1\r\n")
    bot.health_check()
    await bot.client.setup_hook()
    await bot.client.close()
    assert not bot._background


@pytest.mark.asyncio
async def test_job_shutdown_preserves_retryable_work():
    bot = Bot("offline", slash_only=True, storage=":memory:")
    started = asyncio.Event()
    @bot.job("wait")
    async def wait(payload):
        started.set()
        await asyncio.Event().wait()
    job_id = bot.jobs.schedule("wait")
    task = asyncio.create_task(bot.jobs.run_pending())
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert bot.jobs.status(job_id)["status"] == "pending"
    await bot.client.close()
