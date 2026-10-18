"""Exercise an installed wheel from outside its source checkout (no Discord I/O)."""

import asyncio
from importlib.resources import files
from importlib.metadata import distribution
import json
import tempfile
from pathlib import Path

from discord_bot_maker import Bot, Embed, Engine, Context, Simulator, Checks, Settings, __version__


async def main():
    with tempfile.TemporaryDirectory(prefix="dbm-installed-data-") as directory:
        bot = Bot("offline-token", slash_only=True, storage=Path(directory) / "bot.sqlite3")
        bot.reply("hello", Embed("Hello, {{user.display_name}}!"))

        @bot.command(description="Add numbers")
        def add(first: int, second: int = 1):
            return str(first + second)

        assert [option.name for option in bot.client.tree.get_command("add").parameters] == ["first", "second"]
        bot.store.set("setting", {"ready": True})
        bot.store.close()
        assert bot.store.get("setting") == {"ready": True}
        async with Simulator(bot) as sim:
            assert (await sim.command("add", options={"first": 2})).content == "3"
        assert bot.settings(10, Settings(1, {"enabled": True})).get()["enabled"]
        assert bot.validate_config()["valid"]
        assert bot.sync_preview([])["changes"][0]["action"] == "add"
        await bot.client.close()
        dual = Bot("offline-token", prefix="!", help_command=False, storage=":memory:")
        @dual.command(mode="both", checks=Checks(server_only=True))
        def greet(name: str):
            return f"Hello {name}"
        dual.help(mode="both")
        async with Simulator(dual) as sim:
            assert (await sim.command("greet", mode="prefix", arguments='"Sam Smith"')).content == "Hello Sam Smith"
        await dual.client.close()
        static = Bot("offline-token", slash_only=True)
        static.reply("hello", "Hello, {{user.display_name}}!")
        result = Engine(static.to_definition()).execute("hello", Context(display_name="Sam"))
        assert result["messages"][0]["content"] == "Hello, Sam!"
        await static.client.close()
    installed_files = distribution("discord-bot-maker").files or []
    assert any(str(file) == "discord_bot_maker/py.typed" for file in installed_files)
    for name in ("AGENTS.md", "CLAUDE.md"):
        assert files("discord_bot_maker").joinpath(name).read_text(encoding="utf-8").strip()
    print(json.dumps({"version": __version__, "installed_smoke": "passed"}))


if __name__ == "__main__":
    asyncio.run(main())
