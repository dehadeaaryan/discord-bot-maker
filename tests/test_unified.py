"""Offline contracts for the 2.1 facade, through production adapters."""
from types import SimpleNamespace
from typing import Literal
from unittest.mock import AsyncMock

import discord
import pytest
import pytest_asyncio

from discord_bot_maker import Attachment, Bot, BotConfig, Button, Checks, Embed, Message, Modal, Select, Simulator, TextInput


@pytest_asyncio.fixture
async def bot():
    bot = Bot("offline-placeholder", prefix="!", help_command=False, storage=":memory:")
    yield bot
    await bot.client.close()


@pytest.mark.asyncio
async def test_shared_conversion_validation_and_cooldown(bot):
    calls = []
    @bot.command(mode="both", cooldown=5)
    def add(first: int, second: int = 2):
        calls.append(first)
        return str(first + second)
    async with Simulator(bot) as sim:
        assert (await sim.command("add", mode="prefix", arguments="3")).content == "5"
        assert "cooldown" in (await sim.command("add", options={"first": 3})).content
        sim.advance(5)
        assert (await sim.command("add", options={"first": 4})).content == "6"
        sim.advance(5)
        assert "Invalid" in (await sim.command("add", options={"first": True})).content
        assert "Missing" in (await sim.command("add")).content
        assert "Expected" in (await sim.command("add", mode="prefix", arguments="x")).content
        assert (await sim.command("add", options={"first": 4})).content == "6"
    assert calls == [3, 4, 4]


@pytest.mark.asyncio
async def test_prefix_quotes_bool_literal_and_errors(bot):
    @bot.command(mode="both")
    def choose(text: str, enabled: bool, choice: Literal["a", "b"] = "a"):
        return f"{text}:{enabled}:{choice}"
    async with Simulator(bot) as sim:
        assert (await sim.command("choose", mode="prefix", arguments='"two words" yes b')).content == "two words:True:b"
        assert "Invalid" in (await sim.command("choose", mode="prefix", arguments="x true c")).content
        assert "Too many" in (await sim.command("choose", mode="prefix", arguments="a yes b c")).content
        @bot.on_error
        def errors(ctx, error):
            return "Handled"
        assert (await sim.command("choose")).content == "Handled"


@pytest.mark.asyncio
async def test_checks_help_and_click_reauthorization(bot):
    @bot.command(mode="both", category="Admin", checks=Checks(server_only=True, channels=(20,), roles=(99,), age_restricted=True))
    def secret():
        return Message("Protected", buttons=[Button("Go", reply="Allowed")])
    bot.help(mode="both", page_size=1)
    async with Simulator(bot) as sim:
        denied = await sim.command("secret", roles=(99,))
        assert "age-restricted" in denied.content
        allowed = await sim.command("secret", roles=(99,), age_restricted=True)
        assert "role" in (await sim.click(allowed)).content
        assert (await sim.click(allowed, roles=(99,), age_restricted=True)).content == "Allowed"
        help_result = await sim.command("help", options={"query": "secret"})
        assert "No matching" in help_result.messages[-1]["embed"].description
        visible = await sim.command("help", roles=(99,), age_restricted=True)
        assert "secret" in visible.messages[-1]["embed"].description
        await sim.expire(visible)
        assert all(item.disabled for item in visible.view.children)


@pytest.mark.asyncio
async def test_config_and_rich_responses(bot):
    configured = Bot("offline", slash_only=True, storage=":memory:", config=BotConfig(presence="with commands", allowed_mentions=discord.AllowedMentions(users=True)))
    assert configured.client.activity.name == "with commands"
    assert configured.validate_config()["valid"]
    @configured.command()
    def rich():
        return Message(embed=Embed("Title", fields=(("Name", "Value"),), footer="Footer", thumbnail_url="https://example.com/a.png"), attachments=[Attachment("a.txt", b"hello")], selects=[Select("Pick", ["one", "two"], lambda ctx, value: value)])
    async with Simulator(configured) as sim:
        result = await sim.command("rich")
        payload = result.messages[-1]
        assert payload["embed"].fields[0].value == "Value"
        assert payload["files"][0].filename == "a.txt"
        assert payload["allowed_mentions"].users
        assert (await sim.click(result, value="two")).content == "two"
    await configured.client.close()


@pytest.mark.asyncio
async def test_modal_and_autocomplete(bot):
    @bot.command(defer=False, autocomplete={"topic": lambda ctx, current: [current + " one"]})
    def form(topic: str):
        return Modal(topic, [TextInput("answer", "Answer")], lambda ctx, values: values["answer"])
    async with Simulator(bot) as sim:
        result = await sim.command("form", options={"topic": "Question"})
        assert result.modal.title == "Question"
        assert (await sim.submit(result, {"answer": "Yes"})).content == "Yes"
        provider = bot.client.tree.get_command("form")._params["topic"].autocomplete
        interaction, _ = sim.interaction()
        assert (await provider(interaction, "a"))[0].value == "a one"


@pytest.mark.asyncio
async def test_hooks_are_isolated_and_packs_are_explicit(bot, caplog):
    calls = []
    @bot.on("member_join")
    def broken(member):
        raise RuntimeError("do-not-log-this-secret")
    @bot.on("member_join")
    def welcome(member):
        calls.append(member.id)
    async with Simulator(bot) as sim:
        await sim.event("member_join", SimpleNamespace(id=1))
    assert calls == [1]
    assert bot.client.intents.members
    assert "do-not-log-this-secret" not in caplog.text
    def pack(bot):
        bot.reply("packed", "Hello")
    bot.use(pack)
    with pytest.raises(ValueError, match="already"):
        bot.use(pack)


@pytest.mark.asyncio
async def test_sync_diff_is_read_only_and_detailed(bot):
    bot.reply("hello", "Hello")
    local = bot.client.tree.get_command("hello").to_dict(bot.client.tree)
    snapshot = [dict(local, id="1", application_id="2", version="3")]
    assert bot.sync_preview(snapshot)["changes"][0]["action"] == "unchanged"
    snapshot[0]["description"] = "Old"
    snapshot.append({"name": "old", "type": 1, "description": "Old"})
    result = bot.sync_preview(snapshot)
    assert [item["action"] for item in result["changes"]] == ["change", "remove"]
    assert result["changes"][0]["before"]["description"] == "Old"
    assert result["changes"][0]["after"]["description"] == "A bot command"
    bot.client.tree.fetch_commands = AsyncMock(return_value=[])
    assert (await bot.fetch_sync_preview())["changes"][0]["action"] == "add"


def test_invalid_configuration_and_registration():
    with pytest.raises(ValueError, match="message_content"):
        Bot("offline", config=BotConfig(intents=discord.Intents.default()))
    bot = Bot("offline", slash_only=True, storage=":memory:")
    with pytest.raises(ValueError, match="slash_only"):
        bot.command(mode="both")
    with pytest.raises(ValueError, match="Private"):
        Bot("offline", storage=":memory:").command(mode="both", private=True)
    with pytest.raises(ValueError, match="6000"):
        Embed("t", description="x" * 4000, footer="y" * 2000)


@pytest.mark.asyncio
async def test_gateway_prefix_dispatch_uses_discord_parser(bot):
    @bot.command(mode="both")
    def greet(name: str, enabled: bool = True):
        return f"{name}:{enabled}"
    bot.client._connection.user = SimpleNamespace(id=999)
    # Use the actual discord.py command parser/invocation, with only transport I/O faked.
    channel = SimpleNamespace(id=20, permissions_for=lambda user: SimpleNamespace())
    message = SimpleNamespace(id=100, author=SimpleNamespace(id=1, bot=False, name="Sam", display_name="Sam"), guild=None, channel=channel, content='!greet "Sam Smith" no', attachments=[], _state=bot.client._connection)
    context = await bot.client.get_context(message)
    context.send = AsyncMock()
    await bot.client.invoke(context)
    assert context.send.call_args.kwargs["content"] == "Sam Smith:False"
    assert "ephemeral" not in context.send.call_args.kwargs


@pytest.mark.asyncio
async def test_sync_real_remote_roundtrip_has_no_option_noise(bot):
    from discord import app_commands
    @bot.command()
    def command(value: int = 1):
        return str(value)
    local = bot.client.tree.get_command("command").to_dict(bot.client.tree)
    remote = app_commands.AppCommand(data=dict(local, id="1", application_id="2", version="3"), state=bot.client._connection)
    bot.client.tree.fetch_commands = AsyncMock(return_value=[remote])
    assert (await bot.fetch_sync_preview())["changes"][0]["action"] == "unchanged"
    remote.nsfw = True
    assert (await bot.fetch_sync_preview())["changes"][0]["before"]["nsfw"] is True


@pytest.mark.asyncio
async def test_help_pagination_search_category_and_permission_change(bot):
    for name in ("one", "two", "three"):
        bot.command(name, category="Numbers")(lambda: "Number")
    bot.help(page_size=1)
    async with Simulator(bot) as sim:
        result = await sim.command("help")
        assert "one" in result.messages[-1]["embed"].description
        next_page = await sim.click(result, 1)
        assert "two" in next_page.messages[-1]["embed"].description
        picked = await sim.click(result, 2, value="0")
        assert "help" in picked.messages[-1]["embed"].description
        assert "three" in (await sim.command("help", options={"query": "three"})).messages[-1]["embed"].description
        stranger = await sim.click(result, 2, value="__all__", user_id=2)
        assert "belongs" in stranger.content


@pytest.mark.asyncio
async def test_button_can_open_modal_without_deferring(bot):
    @bot.command()
    def start():
        return Message("Open", buttons=[Button("Form", reply=lambda ctx: Modal("Form", [TextInput("x", "X")], lambda ctx, values: values["x"]), defer=False)])
    async with Simulator(bot) as sim:
        result = await sim.command("start")
        form = await sim.click(result)
        assert form.modal.title == "Form"
        assert (await sim.submit(form, {"x": "Done"})).content == "Done"
