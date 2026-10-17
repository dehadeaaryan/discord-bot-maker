"""Regenerate schema, example and OpenAPI contracts from the Python authority."""
import json
from pathlib import Path

from apps.api.main import app
from discord_bot_maker import BotDefinition
from discord_bot_maker.templates import template

Path("schema").mkdir(exist_ok=True)
Path("schema/bot-definition.json").write_text(json.dumps(BotDefinition.model_json_schema(), indent=2) + "\n")
Path("schema/openapi.json").write_text(json.dumps(app.openapi(), indent=2) + "\n")
for name in ("greeting", "rules", "faq"):
    Path(f"examples/{name}.json").write_text(template(name).model_dump_json(indent=2) + "\n")
Path("examples/hello.json").write_text(template().model_dump_json(indent=2) + "\n")
Path("apps/web/src/lib/hello.json").write_text(template().model_dump_json(indent=2) + "\n")
