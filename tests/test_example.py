import os
import subprocess
import sys

import pytest

from discord_bot_maker import Context, Engine, FlowBot
from discord_bot_maker.example import build_definition


@pytest.mark.parametrize("command", ["hello", "ping", "rules"])
def test_example_replies(command):
    definition = build_definition()
    result = Engine(definition).execute(command, Context())
    assert result["messages"]
    assert result["messages"][0]["kind"] in {"reply", "embed"}


def test_channel_restriction_is_shared_by_preview_and_live_definition():
    definition = build_definition("123456789")
    denied = Engine(definition).execute("hello", Context(channel_id="987654321"))
    assert denied["messages"] == [{"kind": "reply", "content": "Try this command in <#123456789>.", "ephemeral": True}]
    allowed = Engine(definition).execute("hello", Context(channel_id="123456789"))
    assert allowed["messages"][0]["kind"] == "embed"
    client = FlowBot(definition, guild_id=123)
    assert {command.name for command in client.tree.get_commands()} == {"hello", "ping", "rules"}
    assert not client.intents.message_content
    assert not client.intents.members
    assert not client.intents.presences


def test_example_runs_offline_without_token():
    env = {key: value for key, value in os.environ.items() if key not in {"DISCORD_BOT_TOKEN", "DISCORD_GUILD_ID", "DISCORD_CHANNEL_ID"}}
    process = subprocess.run([sys.executable, "examples/bot.py", "--preview", "ping"], env=env, text=True, capture_output=True)
    assert process.returncode == 0, process.stderr
    assert "Pong!" in process.stdout


def test_invalid_server_id_has_actionable_error():
    process = subprocess.run([sys.executable, "examples/bot.py", "--guild-id", "my-server"], text=True, capture_output=True)
    assert process.returncode == 2
    assert "numeric ID" in process.stderr
