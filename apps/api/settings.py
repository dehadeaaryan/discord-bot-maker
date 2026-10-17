"""Environment configuration; production fails closed on missing secrets."""

import os
from urllib.parse import urlsplit
from dataclasses import dataclass, field

from cryptography.fernet import Fernet


@dataclass
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./development.db"))
    origin: str = field(default_factory=lambda: os.getenv("PUBLIC_ORIGIN", "http://localhost:5173").rstrip("/"))
    encryption_key: str = field(default_factory=lambda: os.getenv("ENCRYPTION_KEY", ""))
    client_id: str = field(default_factory=lambda: os.getenv("DISCORD_CLIENT_ID", ""))
    client_secret: str = field(default_factory=lambda: os.getenv("DISCORD_CLIENT_SECRET", ""))
    hosted_owner_id: str = field(default_factory=lambda: os.getenv("HOSTED_OWNER_ID", ""))
    allow_dev_login: bool = field(default_factory=lambda: os.getenv("ALLOW_DEV_LOGIN") == "1")
    production: bool = field(default_factory=lambda: os.getenv("APP_ENV") == "production")
    hosting_enabled: bool = field(default_factory=lambda: os.getenv("ENABLE_HOSTING") == "1")
    max_bots: int = field(default_factory=lambda: int(os.getenv("MAX_HOSTED_BOTS", "3")))

    def __post_init__(self):
        origin = urlsplit(self.origin)
        if origin.scheme not in {"http", "https"} or not origin.hostname or origin.username or origin.password or origin.path not in {"", "/"} or origin.query or origin.fragment:
            raise ValueError("PUBLIC_ORIGIN must be an HTTP(S) origin without a path or credentials.")
        if bool(self.client_id) != bool(self.client_secret):
            raise ValueError("Configure both Discord OAuth credentials or leave both empty.")
        if not 1 <= self.max_bots <= 10:
            raise ValueError("MAX_HOSTED_BOTS must be between 1 and 10.")
        if self.production:
            if origin.scheme != "https" or not self.encryption_key or not self.database_url.startswith("postgresql"):
                raise ValueError("Production requires HTTPS PUBLIC_ORIGIN, ENCRYPTION_KEY and PostgreSQL DATABASE_URL.")
            if self.allow_dev_login:
                raise ValueError("Development login cannot be enabled in production.")
            if self.hosting_enabled and not (self.hosted_owner_id and self.client_id):
                raise ValueError("Production hosting requires HOSTED_OWNER_ID and Discord OAuth credentials.")
        if not self.encryption_key:
            # Development credentials deliberately stop working after restart.
            self.encryption_key = Fernet.generate_key().decode()
        Fernet(self.encryption_key.encode())

    @property
    def redirect_uri(self):
        return f"{self.origin}/api/auth/callback"
