# app/core/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import urlparse
import os

class Settings(BaseSettings):
    # App
    APP_NAME: str = "SETS-Chatbot"
    APP_VERSION: str = "0.1.1"
    APP_DESCRIPTION: str | None = None
    APP_AUTHOR: str | None = None

    # DB
    MONGODB_URI: str = ""
    MONGODB_CONNECTION_STRING: str = ""  # legacy
    DB_NAME: str | None = None

    # Collections
    USERS_COLLECTION: str = "users"
    SESSIONS_COLLECTION: str = "sessions"
    QA_COLLECTION: str = "qa_history"
    FEEDBACK_COLLECTION: str = "feedback"
    FILES_COLLECTION: str = "files"

    # Auth
    SECRET_KEY: str = "CHANGE_ME"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # helpers
    @property
    def mongo_uri(self) -> str:
        return self.MONGODB_URI or self.MONGODB_CONNECTION_STRING

    @property
    def mongo_db_name(self) -> str | None:
        if self.DB_NAME:
            return self.DB_NAME
        try:
            parsed = urlparse(self.mongo_uri)
            if parsed.path and parsed.path != "/":
                return parsed.path.lstrip("/")
        except Exception:
            pass
        return None

# ✅ global singleton
settings = Settings()

# ✅ cached getter (for imports in app.core.__init__)
@lru_cache
def get_settings() -> Settings:
    return settings
