"""Opt-in durable named jobs. One running bot per SQLite storage file."""
import asyncio
import json
import logging
import math
import time
import uuid
from .interactions import invoke

logger = logging.getLogger(__name__)


class Jobs:
    def __init__(self, bot):
        self.bot = bot
        self.handlers = {}
        self.active = {}
        self._clock = time.time

    def _table(self, connection):
        connection.execute("CREATE TABLE IF NOT EXISTS dbm_jobs (id TEXT PRIMARY KEY, name TEXT NOT NULL, payload TEXT NOT NULL, due REAL NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, retries INTEGER NOT NULL, status TEXT NOT NULL)")

    def schedule(self, name, *, delay=0, payload=None, retries=3):
        if name not in self.handlers:
            raise ValueError("Register the named job before scheduling it.")
        if not math.isfinite(delay) or delay < 0 or type(retries) is not int or not 0 <= retries <= 10:
            raise ValueError("Jobs need a nonnegative delay and 0–10 retries.")
        encoded = json.dumps(payload, allow_nan=False)
        if len(encoded.encode()) > 65536:
            raise ValueError("Job payload must be smaller than 64 KiB.")
        job_id = uuid.uuid4().hex
        with self.bot.store._database.transaction() as connection:
            self._table(connection)
            connection.execute("INSERT INTO dbm_jobs(id,name,payload,due,retries,status) VALUES(?,?,?,?,?,'pending')", (job_id, name, encoded, self._clock() + delay, retries))
        return job_id

    def status(self, job_id):
        with self.bot.store._database.transaction() as connection:
            self._table(connection)
            row = connection.execute("SELECT status,attempts FROM dbm_jobs WHERE id=?", (job_id,)).fetchone()
            return {"status": row[0], "attempts": row[1]} if row else None

    def cancel(self, job_id):
        with self.bot.store._database.transaction() as connection:
            self._table(connection)
            changed = connection.execute("UPDATE dbm_jobs SET status='cancelled' WHERE id=? AND status IN ('pending','running')", (job_id,)).rowcount
        task = self.active.get(job_id)
        if changed and task:
            task.cancel()
        return bool(changed)

    def recover(self):
        with self.bot.store._database.transaction() as connection:
            self._table(connection)
            connection.execute("UPDATE dbm_jobs SET status='pending' WHERE status='running'")

    async def run_pending(self):
        """Execute one due job; also usable in deterministic offline tests."""
        with self.bot.store._database.transaction() as connection:
            self._table(connection)
            row = connection.execute("SELECT id,name,payload,attempts,retries FROM dbm_jobs WHERE status='pending' AND due<=? ORDER BY due,id LIMIT 1", (self._clock(),)).fetchone()
            if row is None:
                return False
            job_id, name, payload, attempts, retries = row
            connection.execute("UPDATE dbm_jobs SET status='running', attempts=attempts+1 WHERE id=?", (job_id,))
        async def execute():
            if name not in self.handlers:
                raise ValueError("Job handler is not registered.")
            await invoke(self.handlers[name], json.loads(payload))
        task = asyncio.create_task(execute())
        self.active[job_id] = task
        status, due = "done", self._clock()
        try:
            await task
        except asyncio.CancelledError:
            # Explicit cancellation stays cancelled; shutdown makes it retryable.
            status = "pending"
            if self.status(job_id)["status"] != "cancelled" or getattr(asyncio.current_task(), "cancelling", lambda: False)():
                raise
        except Exception as error:
            logger.warning("Job %s failed (%s).", name, type(error).__name__)
            status = "pending" if attempts < retries else "failed"
            due += min(3600, 2 ** (attempts + 1))
        finally:
            self.active.pop(job_id, None)
            with self.bot.store._database.transaction() as connection:
                connection.execute("UPDATE dbm_jobs SET status=?,due=? WHERE id=? AND status='running'", (status, due, job_id))
        return True

    async def run(self):
        self.recover()
        await self.bot.client.wait_until_ready()
        while True:
            if not await self.run_pending():
                await asyncio.sleep(1)
