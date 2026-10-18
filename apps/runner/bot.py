"""One bot process, killed if its supervisor dies or its lease expires."""

import asyncio
import json
import os
from pathlib import Path
import sys
import time

from sqlalchemy import select, update

from apps.api.db import Project, connect
from apps.api.settings import Settings
from discord_bot_maker import BotDefinition, FlowBot


async def main():
    data = json.load(sys.stdin)
    settings = Settings()
    _, sessions = connect(settings.database_url)

    class HostedBot(FlowBot):
        async def on_ready(self):
            with sessions.begin() as session:
                session.execute(update(Project).where(Project.id == data["project_id"], Project.lease_owner == data["lease_owner"], Project.lease_until > time.time()).values(observed_state="online", synced_revision=data["revision_id"]))

    bot = HostedBot(BotDefinition.model_validate(data["definition"]), sync_commands=data["sync"], guild_id=int(data["guild_id"]) if data["guild_id"] else None, storage=Path(os.environ.get("BOT_DATA_DIR", "data/hosted")) / f"{data['project_id']}.sqlite3")

    async def watch_lease():
        while True:
            try:
                with sessions() as session:
                    project = session.get(Project, data["project_id"])
                    valid = project and project.lease_owner == data["lease_owner"] and project.lease_until > time.time() + 5 and project.desired_state == "running" and project.published_revision == data["revision_id"]
                if not valid:
                    await bot.close()
                    return
            except Exception:
                await bot.close()
                return
            await asyncio.sleep(2)

    bot.dbm._manage_signals = True
    watcher = asyncio.create_task(watch_lease())
    try:
        await bot.start(data.pop("token"))
    finally:
        watcher.cancel()
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
