from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import urlparse
import os

class Settings(BaseSettings):
    # App
    APP_NAME: str = "SETS-Chatbot"
    APP_VERSION: str = "0.1.1"
    APP_DESCRIPTION: str | None = None
    APP_AUTHOR: str | None = None

    # DB – accept both old and new var names
    MONGODB_URI: str = ""
    MONGODB_CONNECTION_STRING: str = ""  # legacy name (v1)
    DB_NAME: str | None = None

    # Collections (keep same names as v1)
    USERS_COLLECTION: str = "users"
    SESSIONS_COLLECTION: str = "sessions"
    QA_COLLECTION: str = "qa_history"
    FEEDBACK_COLLECTION: str = "feedback"
    FILES_COLLECTION: str = "files"

    # Auth (if you added JWT)
    SECRET_KEY: str = "CHANGE_ME"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # derive final connection string & db
    @property
    def mongo_uri(self) -> str:
        return self.MONGODB_URI or self.MONGODB_CONNECTION_STRING

    @property
    def mongo_db_name(self) -> str | None:
        # Prefer explicit DB_NAME; otherwise parse from URI path (e.g. .../chat_db)
        if self.DB_NAME:
            return self.DB_NAME
        try:
            parsed = urlparse(self.mongo_uri)
            if parsed.path and parsed.path != "/":
                return parsed.path.lstrip("/")
        except Exception:
            pass
        return None

settings = Settings()

# sanity: if uri is missing, allow overriding via env at runtime
if not settings.mongo_uri:
    settings.MONGODB_URI = os.getenv("MONGODB_URI", "")
