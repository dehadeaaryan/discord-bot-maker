import io
import json
import zipfile

import pytest
from pydantic import ValidationError

from discord_bot_maker import BotDefinition, Context, Engine, ExecutionError, FlowBot
from discord_bot_maker.export import export_archive
from discord_bot_maker.templates import template


def test_template_roundtrip_export_and_discord_registration():
    definition = template()
    loaded = BotDefinition.model_validate_json(definition.model_dump_json())
    assert Engine(loaded).execute("hello", Context(display_name="Sam"))["messages"][0]["content"] == "Hello, Sam! 👋"
    with zipfile.ZipFile(io.BytesIO(export_archive(loaded))) as archive:
        assert set(archive.namelist()) == {"bot.json", "run_bot.py", "requirements.txt", "README.md"}
        assert json.loads(archive.read("bot.json")) == loaded.model_dump(mode="json")
        assert "token" not in archive.read("bot.json").decode().lower()
        compile(archive.read("run_bot.py"), "run_bot.py", "exec")
    client = FlowBot(loaded)
    assert [command.name for command in client.tree.get_commands()] == ["hello"]
    assert not client.intents.message_content


def conditional_definition():
    definition = template().model_dump(mode="json")
    definition["nodes"] += [
        {"id": "condition", "kind": "condition", "field": "role", "value": "123"},
        {"id": "denied", "kind": "reply", "content": "Members only"},
    ]
    definition["edges"] = [
        {"id": "a", "source": "command-1", "target": "condition"},
        {"id": "b", "source": "condition", "target": "reply-1", "branch": "true"},
        {"id": "c", "source": "condition", "target": "denied", "branch": "false"},
    ]
    return definition


def test_condition_branches_and_cooldown():
    definition = conditional_definition()
    definition["nodes"][0]["cooldown"] = 10
    now = [100.0]
    engine = Engine(BotDefinition.model_validate(definition), clock=lambda: now[0])
    assert engine.execute("hello", Context(role_ids=[]))["messages"][0]["content"] == "Members only"
    with pytest.raises(ExecutionError, match="cooldown"):
        engine.execute("hello", Context(role_ids=["123"]))
    now[0] += 11
    result = engine.execute("hello", Context(role_ids=["123"]))
    assert result["trace"][1]["result"] == "true"
    assert "Hello" in result["messages"][0]["content"]


@pytest.mark.parametrize("mutation", [
    lambda d: d["edges"].append({"id": "loop", "source": "reply-1", "target": "reply-1"}),
    lambda d: d["edges"][0].update(target="missing"),
    lambda d: d["nodes"][1].update(content="{{unknown}}"),
    lambda d: d["nodes"][1].update(content="{{user.name}"),
    lambda d: d["nodes"].append({"id": "unreachable", "kind": "reply", "content": "Hi"}),
    lambda d: d.update(token="secret"),
    lambda d: d["nodes"][0].update(name="invalid name"),
])
def test_invalid_definitions_are_rejected(mutation):
    definition = template().model_dump(mode="json")
    mutation(definition)
    with pytest.raises(ValidationError):
        BotDefinition.model_validate(definition)


def test_rendered_limits_are_enforced():
    definition = template()
    with pytest.raises(ExecutionError, match="limit"):
        Engine(definition).execute("hello", Context(display_name="x" * 2100))


def test_missing_condition_branch_rejected():
    definition = conditional_definition()
    definition["edges"].pop()
    with pytest.raises(ValidationError, match="True and one False"):
        BotDefinition.model_validate(definition)
