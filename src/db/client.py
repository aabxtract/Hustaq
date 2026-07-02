import motor.motor_asyncio
from src.lib.config import get_settings

_client: motor.motor_asyncio.AsyncIOMotorClient | None = None
_db = None

def get_db():
    global _client, _db
    if _client is None:
        settings = get_settings()
        _client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URI)
        _db = _client.hustaq
    return _db
