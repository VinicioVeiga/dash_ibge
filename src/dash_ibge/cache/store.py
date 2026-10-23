from __future__ import annotations

import json
import threading
import time
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit

from dash_ibge.config import Settings, get_settings


class ResponseCache(Protocol):
    backend: str
    detail: str

    def get(self, key: str) -> object | None: ...

    def set(self, key: str, value: object, ttl_seconds: int) -> None: ...

    def close(self) -> None: ...


class MemoryCache:
    backend = "memoria"

    def __init__(self, detail: str = "Redis indisponível; cache em memória neste processo.") -> None:
        self.detail = detail
        self._values: dict[str, tuple[float, str]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> object | None:
        now = time.monotonic()
        with self._lock:
            item = self._values.get(key)
            if item is None:
                return None
            expires, raw = item
            if expires < now:
                self._values.pop(key, None)
                return None
        return json.loads(raw)

    def set(self, key: str, value: object, ttl_seconds: int) -> None:
        raw = json.dumps(value, ensure_ascii=False)
        with self._lock:
            self._values[key] = (time.monotonic() + ttl_seconds, raw)

    def close(self) -> None:
        return None


class RedisCache:
    backend = "redis"

    def __init__(self, url: str) -> None:
        import redis

        self.url = url
        self.detail = f"Redis em {redact_url(url)}"
        self.client = redis.Redis.from_url(
            url,
            socket_connect_timeout=0.4,
            socket_timeout=0.8,
            decode_responses=True,
        )

    def ping(self) -> None:
        self.client.ping()

    def get(self, key: str) -> object | None:
        raw = self.client.get(_key(key))
        if raw is None:
            return None
        return json.loads(raw)

    def set(self, key: str, value: object, ttl_seconds: int) -> None:
        self.client.setex(_key(key), ttl_seconds, json.dumps(value, ensure_ascii=False))

    def close(self) -> None:
        self.client.close()


def open_cache(settings: Settings | None = None) -> ResponseCache:
    settings = settings or get_settings()
    if not settings.redis_enabled:
        return MemoryCache("REDIS_ENABLED=0; cache em memória neste processo.")
    try:
        cache = RedisCache(settings.redis_url)
        cache.ping()
        return cache
    except Exception as exc:
        reason = str(exc).splitlines()[0][:180]
        return MemoryCache(f"Redis não respondeu ({reason}). Cache em memória neste processo.")


def redact_url(url: str) -> str:
    parsed = urlsplit(url)
    if not parsed.password:
        return url
    host = parsed.hostname or ""
    auth = parsed.username or ""
    netloc = f"{auth}:***@{host}"
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def _key(url: str) -> str:
    return f"dash-ibge:{url}"
