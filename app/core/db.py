from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

_client = None
_db: AsyncIOMotorDatabase | None = None

def get_db() -> AsyncIOMotorDatabase:
    global _client, _db
    if _db is None:
        uri = settings.mongo_uri
        if not uri:
            raise RuntimeError("Mongo URI not configured. Set MONGODB_URI or MONGODB_CONNECTION_STRING")
        _client = AsyncIOMotorClient(uri, appname="sets_chatbot_v2")
        db_name = settings.mongo_db_name
        if not db_name:
            raise RuntimeError("DB name not found. Set DB_NAME or include it in the URI (…/your_db)")
        _db = _client[db_name]
    return _db

def col_users():
    return get_db()[settings.USERS_COLLECTION]

def col_sessions():
    return get_db()[settings.SESSIONS_COLLECTION]

def col_qa():
    return get_db()[settings.QA_COLLECTION]

def col_feedback():
    return get_db()[settings.FEEDBACK_COLLECTION]

def col_files():
    return get_db()[settings.FILES_COLLECTION]
