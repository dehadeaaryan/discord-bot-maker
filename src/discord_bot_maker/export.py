"""Portable export archives using the installed Python library."""

import io
import zipfile

from .definition import BotDefinition

LAUNCHER = '''import os
from pathlib import Path
from discord_bot_maker import BotDefinition, FlowBot

definition = BotDefinition.model_validate_json(Path(__file__).with_name("bot.json").read_text())
# Synchronize only when publishing a changed command definition.
bot = FlowBot(definition, sync_commands=os.getenv("SYNC_COMMANDS") == "1")
bot.run(os.environ["DISCORD_BOT_TOKEN"])
'''


def export_archive(definition: BotDefinition) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("bot.json", definition.model_dump_json(indent=2))
        archive.writestr("run_bot.py", LAUNCHER)
        archive.writestr("requirements.txt", "discord-bot-maker>=2.0.0a1,<3\n")
        archive.writestr("README.md", "# Your Discord bot\n\nInstall the Discord Bot Maker prerelease from this repository until it is published to PyPI.\nThen install requirements.txt, set DISCORD_BOT_TOKEN, and run python run_bot.py.\nSet SYNC_COMMANDS=1 only to publish updated slash commands. Prefix commands require Message Content Intent.\nNever share your token.\n")
    return output.getvalue()
