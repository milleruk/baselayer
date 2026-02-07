from django.conf import settings
import redis

def get_redis_client():
    url = getattr(settings, 'REDIS_URL', None) or getattr(settings, 'CELERY_BROKER_URL', None) or 'redis://localhost:6379/0'
    return redis.from_url(url)


class RedisLock:
    """Simple context-manager for a redis lock (non-blocking acquire).

    Usage:
        with RedisLock(f'fetch:ride:{ride_id}', ttl=120) as acquired:
            if not acquired:
                return
            # do work
    """
    def __init__(self, key, ttl=60):
        self.key = f'lock:{key}'
        self.ttl = ttl
        self._client = None
        self.acquired = False

    def __enter__(self):
        self._client = get_redis_client()
        try:
            self.acquired = self._client.set(self.key, '1', nx=True, ex=self.ttl)
        except Exception:
            self.acquired = False
        return self.acquired

    def __exit__(self, exc_type, exc, tb):
        try:
            if self.acquired:
                self._client.delete(self.key)
        except Exception:
            pass
