"""A small slash-command bot. Run with python -m discord_bot_maker.example."""

import argparse
import getpass
import json
import os
from pathlib import Path

import discord

from .config import read_env
from .dbot import Bot
from .definition import BotDefinition
from .engine import Context, Engine
from .responses import Embed


def load_example_env(path: Path = Path(".env")):
    """Compatibility helper; new bot scripts can simply call Bot.from_env()."""
    for key, value in read_env(path).items():
        os.environ.setdefault(key, value)


def build_bot(token: str, *, guild_id=None, channel_id=None) -> Bot:
    """Three replies using only the public authoring API."""
    bot = Bot(token, slash_only=True, guild_id=guild_id, channel_id=channel_id)
    bot.reply("hello", Embed(
        "Hello, {{user.display_name}}! 👋",
        "Your bot is up and running in **{{server.name}}**.\nTry /ping or /rules next.",
    ), description="Get a friendly greeting", cooldown=3)
    bot.reply("ping", "Pong! 🏓 I’m online and ready.", description="Check whether the bot is online", cooldown=3)
    bot.reply("rules", Embed(
        "A few house rules",
        "1. Be kind and respectful.\n2. Keep conversations in the right channels.\n"
        "3. No spam or unsolicited promotions.\n4. Ask a moderator if you need a hand.\n\n"
        "These are example rules—edit them to suit your server.",
    ), description="Read this server’s starter rules", cooldown=3)
    return bot


def build_definition(channel_id: str | None = None) -> BotDefinition:
    """Preview and export the same public API setup without using credentials."""
    return build_bot("offline-preview", channel_id=channel_id).to_definition("My first Discord bot")


def discord_id(value):
    if not value.isdigit() or not 1 <= len(value) <= 25 or int(value) == 0:
        raise argparse.ArgumentTypeError("Use the numeric ID copied from Discord, not a channel name or invite link.")
    return value


def main():
    parser = argparse.ArgumentParser(description="Run your first Discord bot: /hello, /ping, and /rules.")
    try:
        load_example_env()
    except ValueError as error:
        parser.error(str(error))
    parser.add_argument("--guild-id", type=discord_id, default=os.getenv("DISCORD_GUILD_ID") or None, help="Your server ID (or set DISCORD_GUILD_ID).")
    parser.add_argument("--channel-id", type=discord_id, default=os.getenv("DISCORD_CHANNEL_ID") or None, help="Optional: only answer in this channel.")
    parser.add_argument("--sync", action="store_true", help="Register commands in your server on first run or after changing them.")
    parser.add_argument("--preview", choices=["hello", "ping", "rules"], help="Test a reply offline; no token or server required.")
    args = parser.parse_args()
    definition = build_definition(args.channel_id)
    if args.preview:
        context = Context(channel_id=args.channel_id or "100000002")
        print(json.dumps(Engine(definition).execute(args.preview, context), indent=2, ensure_ascii=False))
        return
    if not args.guild_id:
        parser.error("Add --guild-id YOUR_SERVER_ID. See docs/first-bot.md for setup.")
    token = os.getenv("DISCORD_BOT_TOKEN") or getpass.getpass("Discord bot token (hidden; not saved): ")
    if not token.strip():
        parser.error("A bot token is required.")

    bot = build_bot(token.strip(), guild_id=args.guild_id, channel_id=args.channel_id)
    print("Starting your bot. Try /hello, /ping or /rules after it connects.", flush=True)
    try:
        bot.run(sync=args.sync)
    except discord.LoginFailure:
        parser.exit(1, "Discord rejected the bot token. Reset it in Developer Portal → Bot and try again.\n")
    except discord.Forbidden:
        parser.exit(1, "Discord denied access. Invite the bot to this server with bot and applications.commands scopes, and check the server ID.\n")
    except discord.HTTPException:
        parser.exit(1, "Discord could not complete the request. Check your connection, permissions, and application setup.\n")


if __name__ == "__main__":
    main()
