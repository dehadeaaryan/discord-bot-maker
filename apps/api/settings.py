"""Environment configuration; production fails closed on missing secrets."""

import os
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
    max_bots: int = field(default_factory=lambda: int(os.getenv("MAX_HOSTED_BOTS", "3")))

    def __post_init__(self):
        if self.production:
            if not self.origin.startswith("https://") or not all((self.encryption_key, self.client_id, self.client_secret)):
                raise ValueError("Production requires HTTPS PUBLIC_ORIGIN, ENCRYPTION_KEY and Discord OAuth credentials.")
            if self.allow_dev_login:
                raise ValueError("Development login cannot be enabled in production.")
        if not self.encryption_key:
            # Development credentials deliberately stop working after restart.
            self.encryption_key = Fernet.generate_key().decode()
        Fernet(self.encryption_key.encode())

    @property
    def redirect_uri(self):
        return f"{self.origin}/api/auth/callback"
