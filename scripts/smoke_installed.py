"""Exercise an installed wheel from outside its source checkout (no Discord I/O)."""

import asyncio
from importlib.metadata import distribution
import json
import tempfile
from pathlib import Path

from discord_bot_maker import Bot, Embed, Engine, Context, __version__


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
        await bot.client.close()
        static = Bot("offline-token", slash_only=True)
        static.reply("hello", "Hello, {{user.display_name}}!")
        result = Engine(static.to_definition()).execute("hello", Context(display_name="Sam"))
        assert result["messages"][0]["content"] == "Hello, Sam!"
        await static.client.close()
    files = distribution("discord-bot-maker").files or []
    assert any(str(file) == "discord_bot_maker/py.typed" for file in files)
    print(json.dumps({"version": __version__, "installed_smoke": "passed"}))


if __name__ == "__main__":
    asyncio.run(main())
