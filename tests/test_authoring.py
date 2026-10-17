import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from discord_bot_maker import Bot, Button, CommandContext, Embed, Engine, Context, Message, Poll, Store, UserError
from discord_bot_maker.config import read_env
from discord_bot_maker.reminders import ReminderQueue
from examples.sponge import configure


def interaction(user_id=1, guild_id=10, channel_id=20, *, manage_guild=False, roles=()):
    state = {"done": False}
    async def defer(**kwargs):
        state["done"] = True
    async def send_message(*args, **kwargs):
        state["done"] = True
    response = SimpleNamespace(
        is_done=lambda: state["done"], defer=AsyncMock(side_effect=defer),
        send_message=AsyncMock(side_effect=send_message), edit_message=AsyncMock(),
    )
    message = SimpleNamespace(edit=AsyncMock())
    return SimpleNamespace(
        user=SimpleNamespace(id=user_id, name="Sam", display_name="Sam", roles=[SimpleNamespace(id=value) for value in roles]),
        guild_id=guild_id, guild=SimpleNamespace(id=guild_id, name="Test server") if guild_id else None,
        channel_id=channel_id, channel=SimpleNamespace(id=channel_id, name="general"),
        permissions=SimpleNamespace(manage_guild=manage_guild), response=response,
        followup=SimpleNamespace(send=AsyncMock(return_value=message)),
        original_response=AsyncMock(return_value=message),
    )


@pytest.fixture
def bot():
    return Bot("offline", slash_only=True, storage=":memory:")


async def run(bot, name, ctx=None, **options):
    ctx = ctx or interaction()
    await bot.client.tree.get_command(name).callback(ctx, **options)
    return ctx


def text(ctx):
    return ctx.followup.send.call_args.kwargs.get("content", "")


def test_from_env_is_slash_only_and_does_not_mutate_environment(tmp_path, monkeypatch):
    for key in ("DISCORD_BOT_TOKEN", "DISCORD_GUILD_ID", "DISCORD_CHANNEL_ID"):
        monkeypatch.delenv(key, raising=False)
    path = tmp_path / ".env"
    path.write_text('DISCORD_BOT_TOKEN="test-token"\nDISCORD_GUILD_ID=10\nDISCORD_CHANNEL_ID=20\n')
    bot = Bot.from_env(path, storage=":memory:")
    assert bot.token == "test-token"
    assert (bot.guild_id, bot.channel_id) == (10, 20)
    assert not bot.client.intents.message_content
    assert not bot.client.intents.members
    monkeypatch.setenv("DISCORD_GUILD_ID", "30")
    assert read_env(path)["DISCORD_GUILD_ID"] == "30"
    assert Bot.from_env(path, guild_id=40).guild_id == 40


@pytest.mark.asyncio
async def test_static_reply_matches_portable_preview(bot):
    bot.reply("hello", Embed("Hello {{user.display_name}}", "Welcome to {{server.name}}"))
    ctx = await run(bot, "hello")
    preview = Engine(bot.to_definition()).execute("hello", Context(display_name="Sam", server_name="Test server"))
    embed = ctx.followup.send.call_args.kwargs["embed"]
    assert embed.title == preview["messages"][0]["title"]
    assert embed.description == preview["messages"][0]["description"]
    assert ctx.response.defer.call_args.kwargs == {"ephemeral": False, "thinking": True}
    await bot.client.close()


@pytest.mark.asyncio
async def test_normal_function_types_defaults_and_context(bot):
    main_thread = threading.get_ident()
    threads = []
    @bot.command(description="Add two integers", private=True)
    def add(ctx: CommandContext, first: int, second: int = 2):
        threads.append(threading.get_ident())
        return f"{ctx.user.display_name}: {first + second}"
    registered = bot.client.tree.get_command("add")
    assert [parameter.name for parameter in registered.parameters] == ["first", "second"]
    assert registered.parameters[0].required
    assert not registered.parameters[1].required
    ctx = await run(bot, "add", first=5)
    assert text(ctx) == "Sam: 7"
    assert threads[0] != main_thread
    assert ctx.followup.send.call_args.kwargs["ephemeral"]
    await bot.client.close()


@pytest.mark.asyncio
async def test_async_context_respond_does_not_send_twice(bot):
    @bot.command()
    async def answer(ctx: CommandContext, enabled: bool):
        await ctx.respond("Enabled" if enabled else "Disabled")
    ctx = await run(bot, "answer", enabled=True)
    assert text(ctx) == "Enabled"
    ctx.followup.send.assert_awaited_once()
    await bot.client.close()


@pytest.mark.asyncio
async def test_permissions_channel_roles_and_cooldowns():
    bot = Bot("offline", slash_only=True, guild_id=10, channel_id=20, storage=":memory:")
    executions = []
    @bot.command(permission="manage_guild", role_id=99, cooldown=10)
    def protected():
        executions.append(True)
        return "Allowed"
    for ctx in (interaction(guild_id=11), interaction(channel_id=21), interaction(), interaction(manage_guild=True)):
        await run(bot, "protected", ctx)
        ctx.response.send_message.assert_awaited_once()
        ctx.response.defer.assert_not_awaited()
    assert executions == []
    allowed = await run(bot, "protected", interaction(manage_guild=True, roles=[99]))
    assert text(allowed) == "Allowed"
    limited = await run(bot, "protected", interaction(manage_guild=True, roles=[99]))
    assert "cooldown" in limited.response.send_message.call_args.args[0]
    assert len(executions) == 1
    await bot.client.close()


@pytest.mark.asyncio
async def test_errors_do_not_expose_internal_values(bot):
    @bot.command()
    def broken():
        raise RuntimeError("super-secret-token")
    ctx = await run(bot, "broken")
    assert "super-secret-token" not in str(ctx.followup.send.call_args)
    assert "could not be completed" in ctx.followup.send.call_args.args[0]
    @bot.command()
    def expected():
        raise UserError("Pick a smaller number.")
    ctx = await run(bot, "expected")
    assert ctx.followup.send.call_args.args[0] == "Pick a smaller number."
    calls = ctx.followup.send.call_args_list
    assert len(calls) == 2
    assert "Pick a smaller number" not in calls[0].kwargs["content"]
    assert calls[0].kwargs["ephemeral"] is False
    assert calls[1].kwargs["ephemeral"] is True
    await bot.client.close()


def test_authoring_mistakes_fail_at_registration(bot):
    with pytest.raises(ValueError, match="annotation"):
        @bot.command()
        def missing_annotation(value):
            return value
    with pytest.raises(ValueError, match="Unknown Discord permission"):
        bot.command(permission="administer_the_duck")
    with pytest.raises(ValueError, match="Unknown reply variables"):
        bot.reply("unknown", "Hello {{person.whatever}}")
    bot.reply("hello", "Hi")
    with pytest.raises(ValueError, match="already exists"):
        bot.reply("hello", "Again")
    with pytest.raises(ValueError, match="finite|Cooldown"):
        bot.command(cooldown=float("nan"))


@pytest.mark.asyncio
async def test_buttons_render_handle_clicks_and_expire(bot):
    bot.reply("duck", Message("Pet the duck", buttons=[Button("Pet", reply="Quack!")], owner_only=True))
    ctx = await run(bot, "duck")
    view = ctx.followup.send.call_args.kwargs["view"]
    stranger = interaction(user_id=2)
    await view.children[0].callback(stranger)
    assert "belongs" in stranger.response.send_message.call_args.args[0]
    click = interaction()
    await view.children[0].callback(click)
    assert text(click) == "Quack!"
    await view.on_timeout()
    assert all(child.disabled for child in view.children)
    view.message.edit.assert_awaited_once()
    view.stop()
    await bot.client.close()


@pytest.mark.asyncio
async def test_button_functions_use_the_clicking_user_scoped_store(bot):
    def feed(ctx):
        return f"Snacks: {ctx.user_store.increment('snacks')}"
    bot.reply("duck", Message("Hello", buttons=[Button("Feed", reply=feed)]))
    ctx = await run(bot, "duck")
    view = ctx.followup.send.call_args.kwargs["view"]
    click = interaction(user_id=7)
    await view.children[0].callback(click)
    assert text(click) == "Snacks: 1"
    click = interaction(user_id=8)
    await view.children[0].callback(click)
    assert text(click) == "Snacks: 1"
    view.stop()
    await bot.client.close()


@pytest.mark.asyncio
async def test_poll_changes_votes_instead_of_duplicating(bot):
    bot.poll()
    ctx = await run(bot, "poll", question="Tonight?", choices="Minecraft | Valorant")
    view = ctx.followup.send.call_args.kwargs["view"]
    await view.children[0].callback(interaction(user_id=1))
    await view.children[1].callback(interaction(user_id=1))
    await view.children[0].callback(interaction(user_id=2))
    assert view.votes == {1: 1, 2: 0}
    assert "Minecraft — **1**" in view.embed().description
    assert "Valorant — **1**" in view.embed().description
    failed = interaction(user_id=1)
    failed.response.edit_message.side_effect = RuntimeError("network")
    with pytest.raises(RuntimeError):
        await view.children[0].callback(failed)
    assert view.votes[1] == 1
    view.stop()
    await bot.client.close()


def test_store_persists_scopes_and_atomic_increments(tmp_path):
    path = tmp_path / "store.sqlite3"
    first, second = Store(path), Store(path)
    first.scope("server", 1).set("settings", {"name": "Duck"})
    assert first.scope("server", 2).get("settings") is None
    assert second.scope("server", 1).get("settings") == {"name": "Duck"}
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda number: (first if number % 2 else second).increment("count"), range(100)))
    first.close()
    second.close()
    third = Store(path)
    assert third.get("count") == 100
    third.set("count", "not a number")
    with pytest.raises(ValueError, match="not an integer"):
        third.increment("count")
    assert third.delete("count")
    assert not third.delete("count")
    third.close()


@pytest.mark.asyncio
async def test_context_storage_isolated_by_server_and_user(bot):
    contexts = [CommandContext(bot, interaction(user_id=u, guild_id=g)) for u, g in ((1, 10), (2, 10), (1, 20))]
    contexts[0].user_store.set("snacks", 8)
    contexts[0].store.set("motto", "Quack")
    assert contexts[1].user_store.get("snacks") is None
    assert contexts[1].store.get("motto") == "Quack"
    assert contexts[2].store.get("motto") is None
    await bot.client.close()


@pytest.mark.asyncio
async def test_reminders_persist_and_only_owner_can_cancel(tmp_path):
    bot = Bot("offline", slash_only=True, storage=str(tmp_path / "reminders.sqlite3"))
    bot.reminders()
    ctx = await run(bot, "remind", minutes=1, message="Drink water")
    assert "remind you" in text(ctx)
    pending = bot._queue.pending(1, 10)
    assert len(pending) == 1
    reminder_id = pending[0]["id"]
    other = await run(bot, "cancel_reminder", interaction(user_id=2), reminder_id=reminder_id)
    assert "not found" in other.followup.send.call_args.args[0]
    bot.store.close()
    assert bot._queue.pending(1, 10)[0]["id"] == reminder_id
    assert bot._queue.claim(now=pending[0]["due"] - 1) is None
    job = bot._queue.claim(now=pending[0]["due"] + 1)
    assert job["message"] == "Drink water"
    assert bot._queue.claim(now=pending[0]["due"] + 2) is None
    bot._queue.finish(reminder_id, True)
    assert not bot._queue.pending(1, 10)
    await bot.client.close()


@pytest.mark.asyncio
async def test_delivery_only_mentions_reminder_owner(bot):
    channel = SimpleNamespace(guild=SimpleNamespace(id=10), send=AsyncMock())
    bot.client.get_channel = lambda channel_id: channel
    await bot._deliver_reminder({"channel_id": "20", "server_id": "10", "user_id": "1", "message": "@everyone hello"})
    mentions = channel.send.call_args.kwargs["allowed_mentions"].to_dict()
    assert mentions["users"] == [1]
    assert "everyone" not in mentions["parse"]
    assert "roles" not in mentions["parse"]
    await bot.client.close()


@pytest.mark.asyncio
async def test_sync_and_background_shutdown(bot):
    bot.reply("hello", "Hello")
    bot.guild_id = 10
    bot._sync_commands = True
    bot.client.tree.sync = AsyncMock()
    ready = asyncio.Event()
    bot.client.wait_until_ready = ready.wait
    @bot.every(seconds=60, channel_id=20)
    def heartbeat():
        return "Still here"
    await bot.client.setup_hook()
    assert bot.client.tree.sync.call_args.kwargs["guild"].id == 10
    tasks = list(bot._background)
    assert len(tasks) == 1
    await bot.client.close()
    assert all(task.cancelled() for task in tasks)
    assert not bot._background


def test_welcome_opts_in_to_member_intent(bot):
    assert not bot.client.intents.members
    bot.welcome(20, "Welcome, {{user.display_name}}!")
    assert bot.client.intents.members
    assert not bot.client.intents.message_content


def test_dynamic_code_cannot_be_silently_lost_in_export(bot):
    @bot.command()
    def custom():
        return "Hi"
    with pytest.raises(ValueError, match="cannot be exported"):
        bot.to_definition()


@pytest.mark.asyncio
async def test_sponge_is_a_consumer_of_public_api(bot):
    configure(bot)
    assert {command.name for command in bot.client.tree.get_commands()} == {
        "hello", "ping", "rules", "wisdom", "duck", "feed", "motto", "duck_motto", "poll", "remind", "reminders", "cancel_reminder",
    }
    assert text(await run(bot, "feed")) == "🦆 Quack! You’ve fed the duck 1 time(s)."
    assert text(await run(bot, "feed", interaction(user_id=2))) == "🦆 Quack! You’ve fed the duck 1 time(s)."
    await run(bot, "motto", interaction(manage_guild=True), text="Stay spongy")
    assert text(await run(bot, "duck_motto")) == "Stay spongy"
    await bot.client.close()
