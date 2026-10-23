from __future__ import annotations

import shutil

from dash_ibge.cache.store import open_cache
from dash_ibge.config import Settings, get_settings


def probe_stack(settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    cache = open_cache(settings)
    try:
        redis_info = {"backend": cache.backend, "detalhe": cache.detail}
    finally:
        cache.close()
    spark = _spark_status(settings)
    return {
        "redis": redis_info,
        "spark": spark,
        "llm": {
            "configurado": settings.llm_configured,
            "modelo": settings.llm_model if settings.llm_configured else "",
            "url": settings.llm_base_url if settings.llm_configured else "",
        },
        "jev": {
            "backend": "jev-http" if settings.jev_remote else "jev-local",
            "modelo": settings.jev_model if settings.jev_remote else "logístico local",
        },
        "ibge": settings.ibge_base_url,
        "mcp": "python -m dash_ibge.mcp_server",
    }


def _spark_status(settings: Settings) -> dict:
    mode = settings.spark_enabled
    try:
        import pyspark
    except Exception:
        pyspark = None
    java = shutil.which("java")
    installed = pyspark is not None
    if mode in {"0", "false", "no", "off"}:
        state = "desligado"
    elif installed and java:
        state = "disponivel"
    else:
        state = "ausente"
    return {
        "estado": state,
        "modo": mode,
        "pacote": installed,
        "java": bool(java),
        "versao": getattr(pyspark, "__version__", "") if pyspark else "",
    }
