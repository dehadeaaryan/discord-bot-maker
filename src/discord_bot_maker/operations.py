"""Opt-in JSON logging and an HTTP readiness endpoint."""
import asyncio
import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record):
        # No traceback/exception values: errors may contain secrets from handlers.
        return json.dumps({"time": datetime.fromtimestamp(record.created, timezone.utc).isoformat(), "level": record.levelname, "logger": record.name, "message": record.getMessage()})


def configure_logging(*, level=logging.INFO, stream=None):
    """Configure the package logger only. Application logs remain app-owned."""
    logger = logging.getLogger("discord_bot_maker")
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.handlers[:] = [handler]
    logger.setLevel(level)
    logger.propagate = False
    return logger


async def health_server(bot, host, port):
    async def handle(reader, writer):
        try:
            line = await asyncio.wait_for(reader.readline(), timeout=3)
            if line.startswith(b"GET /health "):
                health = bot.health()
                status = "200 OK" if health["ready"] and not health["closed"] else "503 Service Unavailable"
                payload = json.dumps(health).encode()
            else:
                status, payload = "404 Not Found", b'{}'
            writer.write(f"HTTP/1.1 {status}\r\nContent-Type: application/json\r\nContent-Length: {len(payload)}\r\nConnection: close\r\n\r\n".encode() + payload)
            await writer.drain()
        except (TimeoutError, ConnectionError, ValueError):
            pass
        finally:
            writer.close()
            await writer.wait_closed()
    server = await asyncio.start_server(handle, host, port, limit=4096)
    async with server:
        await server.serve_forever()
