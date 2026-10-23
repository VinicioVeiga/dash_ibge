from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def _flag(name: str, default: str = "1") -> bool:
    return os.getenv(name, default).strip().lower() not in {"0", "false", "no", "off"}


@dataclass(frozen=True)
class Settings:
    ibge_base_url: str
    ibge_timeout: float
    redis_enabled: bool
    redis_url: str
    cache_ttl_seconds: int
    spark_enabled: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    jev_api_url: str
    jev_api_key: str
    jev_model: str

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key.strip())

    @property
    def jev_remote(self) -> bool:
        return bool(self.jev_api_url.strip())


def get_settings() -> Settings:
    return Settings(
        ibge_base_url=os.getenv("IBGE_BASE_URL", "https://servicodados.ibge.gov.br/api/v3").rstrip("/"),
        ibge_timeout=float(os.getenv("IBGE_TIMEOUT", "90")),
        redis_enabled=_flag("REDIS_ENABLED", "1"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", str(60 * 60 * 12))),
        spark_enabled=os.getenv("SPARK_ENABLED", "auto").strip().lower(),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        jev_api_url=os.getenv("JEV_API_URL", "").rstrip("/"),
        jev_api_key=os.getenv("JEV_API_KEY", ""),
        jev_model=os.getenv("JEV_MODEL", "jev"),
    )
