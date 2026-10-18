"""Portable export archives using the installed Python library."""

import io
import zipfile

from .definition import BotDefinition

LAUNCHER = '''import os
from pathlib import Path
from discord_bot_maker import BotDefinition, FlowBot, configure_logging

configure_logging()

definition = BotDefinition.model_validate_json(Path(__file__).with_name("bot.json").read_text())
# Synchronize only when publishing a changed command definition.
bot = FlowBot(definition, sync_commands=os.getenv("SYNC_COMMANDS") == "1")
bot.run(os.environ["DISCORD_BOT_TOKEN"])
'''


EXPORT_README = """# Your Discord bot

## Discord setup

1. Open https://discord.com/developers/applications and choose New Application.
2. Open Bot, add a bot user if prompted, then choose Reset Token. Copy the bot
   token and keep it private. It is not the application ID or public key.
3. Open Installation, enable Guild Install, and select bot and
   applications.commands under Default Install Settings.
4. Select View Channels, Send Messages, and Embed Links, then save.
5. Open the Discord Provided Link, choose Add to Server, and authorize it in a
   server you can manage. Administrator permission is unnecessary.

Leave Interactions Endpoint URL empty: this bot connects through the Gateway.
Slash commands require no privileged intents. For prefix commands, enable
Message Content Intent on the Bot page. Reset your token if it is exposed.

## Install

Create and activate a virtual environment in this extracted folder:

    python -m venv .venv

macOS/Linux: source .venv/bin/activate
Windows PowerShell: .venv\\Scripts\\Activate.ps1

Install the published package:

    python -m pip install -r requirements.txt

## Run

Set your token in the terminal (never put it in bot.json):

macOS/Linux:

    export DISCORD_BOT_TOKEN='your-bot-token'
    SYNC_COMMANDS=1 python run_bot.py

Windows PowerShell:

    $env:DISCORD_BOT_TOKEN='your-bot-token'
    $env:SYNC_COMMANDS='1'
    python run_bot.py

The launcher reads environment variables, not .env files. Keep tokens out of Git
and chat. Sync on first run and after changing slash commands. For later starts,
use python run_bot.py without SYNC_COMMANDS (PowerShell: Remove-Item Env:SYNC_COMMANDS).
Keep the process running, then try your slash command in Discord.

For faster registration in a test server, enable Discord Developer Mode under
User Settings > Advanced, right-click the server, and Copy Server ID. Then run:

    discord-bot-maker run bot.json --sync --guild-id YOUR_SERVER_ID

Replace YOUR_SERVER_ID with that numeric ID. The same DISCORD_BOT_TOKEN environment
variable is used. Omit --guild-id for global command registration.

Package: https://pypi.org/project/discord-bot-maker/
Setup guide: https://github.com/dehadeaaryan/discord-bot-maker/blob/main/docs/first-bot.md
"""


def export_archive(definition: BotDefinition) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("bot.json", definition.model_dump_json(indent=2))
        archive.writestr("run_bot.py", LAUNCHER)
        archive.writestr("requirements.txt", "discord-bot-maker>=2.1.1,<3\n")
        archive.writestr("README.md", EXPORT_README)
    return output.getvalue()
