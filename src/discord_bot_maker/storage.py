"""Lazy SQLite JSON storage with explicit scopes and atomic counters."""

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class _Database:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self.connection: sqlite3.Connection | None = None
        self.lock = threading.RLock()

    def open(self):
        if self.connection is None:
            if self.path != ":memory:":
                Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(self.path, timeout=5, check_same_thread=False)
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("CREATE TABLE IF NOT EXISTS values_store (scope TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY(scope, key))")
            self.connection.commit()
        return self.connection

    @contextmanager
    def transaction(self):
        with self.lock:
            connection = self.open()
            try:
                connection.execute("BEGIN IMMEDIATE")
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise


class Store:
    """Persist JSON values. Scope names isolate server/user data in one file."""

    def __init__(self, path: str | Path = "data/bot.sqlite3", *, _database=None, _scope=()):
        self._database = _database or _Database(path)
        self._scope = _scope

    def scope(self, *parts: str | int) -> "Store":
        """Return a view of the same database, isolated by exact scope components."""
        return Store(_database=self._database, _scope=(*self._scope, *(str(part) for part in parts)))

    @property
    def _namespace(self):
        return json.dumps(self._scope)

    @staticmethod
    def _key(key):
        if not isinstance(key, str) or not 1 <= len(key) <= 128:
            raise ValueError("Storage keys must contain 1–128 characters.")
        return key

    def get(self, key: str, default: Any = None) -> Any:
        with self._database.lock:
            row = self._database.open().execute("SELECT value FROM values_store WHERE scope=? AND key=?", (self._namespace, self._key(key))).fetchone()
            return json.loads(row[0]) if row else default

    def set(self, key: str, value: Any) -> None:
        encoded = json.dumps(value, allow_nan=False)
        if len(encoded.encode()) > 65536:
            raise ValueError("Stored values must be smaller than 64 KiB.")
        with self._database.transaction() as connection:
            connection.execute("INSERT INTO values_store(scope,key,value) VALUES(?,?,?) ON CONFLICT(scope,key) DO UPDATE SET value=excluded.value", (self._namespace, self._key(key), encoded))

    def increment(self, key: str, amount: int = 1) -> int:
        """Atomically increment a counter, including across processes."""
        if type(amount) is not int:
            raise ValueError("Counter increments must be integers.")
        key = self._key(key)
        with self._database.transaction() as connection:
            row = connection.execute("SELECT value FROM values_store WHERE scope=? AND key=?", (self._namespace, key)).fetchone()
            value = json.loads(row[0]) if row else 0
            if type(value) is not int:
                raise ValueError("This storage key is not an integer counter.")
            value += amount
            connection.execute("INSERT INTO values_store(scope,key,value) VALUES(?,?,?) ON CONFLICT(scope,key) DO UPDATE SET value=excluded.value", (self._namespace, key, str(value)))
            return value

    def delete(self, key: str) -> bool:
        with self._database.transaction() as connection:
            return connection.execute("DELETE FROM values_store WHERE scope=? AND key=?", (self._namespace, self._key(key))).rowcount > 0

    def close(self) -> None:
        with self._database.lock:
            if self._database.connection is not None:
                self._database.connection.close()
                self._database.connection = None
