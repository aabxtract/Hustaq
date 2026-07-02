import redis
from src.lib.config import get_settings

_client: redis.Redis | None = None
_redis_available: bool = True


class _NullRedis:
    """A no-op Redis stand-in when Redis is unavailable.
    All operations silently succeed without doing anything,
    so the app degrades gracefully (slower but functional)."""

    def get(self, *a, **kw): return None
    def set(self, *a, **kw): return True
    def setex(self, *a, **kw): return True
    def delete(self, *a, **kw): return 1
    def ping(self): return True
    def __bool__(self): return True


def get_redis() -> redis.Redis:
    global _client, _redis_available

    # If we already know Redis is down, return a no-op stand-in
    if not _redis_available:
        return _NullRedis()  # type: ignore

    if _client is None:
        settings = get_settings()
        try:
            _client = redis.from_url(
                settings.UPSTASH_REDIS_URL,
                decode_responses=True,
            )
            _client.ping()  # Verify connection immediately
            print("[REDIS] Connected successfully")
        except Exception as e:
            print(f"[REDIS] Not available — running without cache: {e}")
            _redis_available = False
            return _NullRedis()  # type: ignore

    return _client
