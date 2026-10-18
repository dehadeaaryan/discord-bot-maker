"""Standalone deployment files, independent of the repository's hosted apps."""
from pathlib import Path

FILES = {
    "bot.py": '''from discord_bot_maker import Bot, configure_logging

configure_logging()
bot = Bot.from_env(storage="/app/data/bot.sqlite3")
bot.reply("hello", "Hello, {{user.display_name}}!")
bot.help()
bot.health_check(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    bot.run()  # Sync explicitly after reviewing a registration preview.
''',
    "requirements.txt": "discord-bot-maker==2.1.0\n",
    "Dockerfile": '''FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home bot && mkdir -p /app/data && chown bot:bot /app/data
COPY --chown=bot:bot bot.py .
USER bot
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"
CMD ["python", "-u", "bot.py"]
''',
    "compose.yaml": '''services:
  bot:
    build: .
    restart: unless-stopped
    init: true
    stop_grace_period: 30s
    environment:
      DISCORD_BOT_TOKEN: ${DISCORD_BOT_TOKEN:?Set DISCORD_BOT_TOKEN}
      DISCORD_GUILD_ID: ${DISCORD_GUILD_ID:-}
    volumes:
      - bot-data:/app/data
    expose:
      - "8080"
volumes:
  bot-data:
''',
    ".dockerignore": ".env\n.git\ndata\n.venv\n__pycache__\n*.sqlite3*\n",
    ".gitignore": ".env\ndata/\n.venv/\n__pycache__/\n",
    "README.md": '''# Standalone bot deployment

Set DISCORD_BOT_TOKEN and optionally DISCORD_GUILD_ID in the deployment environment.
Never put tokens in the Docker image or source. The bot reads exported variables.

For Docker Compose, run `docker compose up --build -d` with those variables set.
For Coolify, create a Docker Compose resource from this directory, set the same
variables, retain the bot-data volume and run one replica. No public domain is
needed for the gateway connection. GET /health on internal port 8080 reports
readiness; avoid exposing it publicly. Configure volume backups separately.

Before deployment, register commands deliberately: authenticate a separate
maintenance client, inspect `await bot.fetch_sync_preview()`, then synchronize
the reviewed scope. Startup does not synchronize automatically. See the package's
2.1 guide for the complete preview workflow. Review changes again if remote
registration or local code changes between preview and sync.

The generated requirements pin 2.1.0, which must be published before an ordinary
registry build succeeds. To test an unreleased checkout, build/install its wheel
in your own image. Templates require an actual container deployment smoke test.
''',
}


def scaffold(directory):
    directory = Path(directory)
    conflicts = [name for name in FILES if (directory / name).exists()]
    if conflicts:
        raise ValueError("Scaffolding refuses to overwrite existing files.")
    directory.mkdir(parents=True, exist_ok=True)
    for name, content in FILES.items():
        (directory / name).write_text(content)
    return sorted(FILES)
