"""Versioned, validated server settings with transactional SQLite migrations."""
from copy import deepcopy
from dataclasses import dataclass, field
import json
from typing import Callable


@dataclass(frozen=True)
class Settings:
    version: int
    defaults: dict
    migrations: dict[int, Callable] = field(default_factory=dict)
    validate: Callable | None = None

    def __post_init__(self):
        if type(self.version) is not int or self.version < 1:
            raise ValueError("Settings version must be a positive integer.")
        json.dumps(self.defaults, allow_nan=False)
        if not isinstance(self.defaults, dict):
            raise TypeError("Settings defaults must be a dictionary.")

    def _validate(self, values):
        if not isinstance(values, dict) or set(values) - set(self.defaults):
            raise ValueError("Unknown server setting.")
        for key, value in values.items():
            if type(value) is not type(self.defaults[key]):
                raise ValueError(f"Invalid type for setting {key}.")
        if self.validate:
            self.validate(values)
        encoded = json.dumps(values, allow_nan=False)
        if len(encoded.encode()) > 65536:
            raise ValueError("Settings must be smaller than 64 KiB.")

    def bind(self, store):
        return ServerSettings(store, self)


class ServerSettings:
    def __init__(self, store, schema):
        self.store, self.schema = store, schema

    def _read(self, connection):
        row = connection.execute("SELECT value FROM values_store WHERE scope=? AND key=?", (self.store._namespace, "__settings__")).fetchone()
        document = json.loads(row[0]) if row else {"version": self.schema.version, "values": deepcopy(self.schema.defaults)}
        version, values = document["version"], document["values"]
        if version > self.schema.version:
            raise ValueError("Stored settings are newer than this application.")
        while version < self.schema.version:
            migration = self.schema.migrations.get(version)
            if migration is None:
                raise ValueError(f"Missing settings migration from version {version}.")
            values = migration(deepcopy(values))
            version += 1
        merged = deepcopy(self.schema.defaults)
        merged.update(values)
        self.schema._validate(merged)
        return {"version": version, "values": merged}

    def _write(self, connection, document):
        connection.execute("INSERT INTO values_store(scope,key,value) VALUES(?,?,?) ON CONFLICT(scope,key) DO UPDATE SET value=excluded.value", (self.store._namespace, "__settings__", json.dumps(document, allow_nan=False)))

    def get(self):
        with self.store._database.transaction() as connection:
            document = self._read(connection)
            self._write(connection, document)
            return deepcopy(document["values"])

    def update(self, **changes):
        with self.store._database.transaction() as connection:
            document = self._read(connection)
            document["values"].update(changes)
            self.schema._validate(document["values"])
            self._write(connection, document)
            return deepcopy(document["values"])
