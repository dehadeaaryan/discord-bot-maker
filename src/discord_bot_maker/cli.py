"""Command-line tools for bot definitions."""

import argparse
import json
import os
from pathlib import Path

from .definition import BotDefinition
from .engine import Context, Engine
from .export import export_archive
from .flow import FlowBot
from .templates import template
from .migration import migrate_commands
from . import __version__


def main():
    parser = argparse.ArgumentParser(prog="discord-bot-maker")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("validate", "preview", "export", "run"):
        command = sub.add_parser(action)
        command.add_argument("definition", type=Path)
        if action == "preview":
            command.add_argument("--command", default="hello")
            command.add_argument("--mode", choices=["slash", "prefix"], default="slash")
            command.add_argument("--context", type=Path)
        if action == "export":
            command.add_argument("--output", type=Path, default=Path("bot.zip"))
        if action == "run":
            command.add_argument("--sync", action="store_true")
            command.add_argument("--guild-id", type=int)
    command = sub.add_parser("template")
    command.add_argument("name", choices=["greeting", "rules", "faq"], default="greeting", nargs="?")
    sub.add_parser("schema")
    command = sub.add_parser("migrate")
    command.add_argument("definition", type=Path, help="JSON export of a v1 command dictionary")
    command.add_argument("--prefix", default="!")
    args = parser.parse_args()
    try:
        if args.action == "schema":
            print(json.dumps(BotDefinition.model_json_schema(), indent=2))
            return
        if args.action == "template":
            print(template(args.name).model_dump_json(indent=2))
            return
        if args.action == "migrate":
            print(migrate_commands(json.loads(args.definition.read_text()), prefix=args.prefix).model_dump_json(indent=2))
            return
        definition = BotDefinition.model_validate_json(args.definition.read_text())
        if args.action == "validate":
            print("Valid bot definition")
        elif args.action == "preview":
            context = Context(**json.loads(args.context.read_text())) if args.context else Context()
            print(json.dumps(Engine(definition).execute(args.command, context, args.mode), indent=2))
        elif args.action == "export":
            args.output.write_bytes(export_archive(definition))
            print(args.output)
        elif args.action == "run":
            FlowBot(definition, sync_commands=args.sync, guild_id=args.guild_id).run(os.environ["DISCORD_BOT_TOKEN"])
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
