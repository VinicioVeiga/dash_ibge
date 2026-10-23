from __future__ import annotations

from urllib.parse import quote, urlencode

import httpx

from dash_ibge.cache.store import ResponseCache
from dash_ibge.config import Settings, get_settings
from dash_ibge.ibge.catalog import AggregateQuery


class IbgeError(RuntimeError):
    pass


def _quote(value: str, safe: str, encoding: str | None = None, errors: str | None = None) -> str:
    return quote(str(value), safe=f"{safe}[]|,", encoding=encoding or "utf-8", errors=errors or "strict")


def build_agregado_url(
    base: str,
    agregado: str,
    periodos: tuple[str, ...] | list[str],
    variaveis: tuple[str, ...] | list[str],
    localidades: str,
    classificacao: str | None = None,
) -> str:
    period = "|".join(periodos)
    variable = "|".join(variaveis)
    url = f"{base.rstrip('/')}/agregados/{agregado}/periodos/{period}/variaveis/{variable}"
    params: dict[str, str] = {"localidades": localidades}
    if classificacao:
        params["classificacao"] = classificacao
    query = urlencode(params, quote_via=_quote)
    return f"{url}?{query}"


class IbgeClient:
    def __init__(self, settings: Settings, cache: ResponseCache, http: httpx.Client | None = None) -> None:
        self.settings = settings
        self.cache = cache
        self._owns_http = http is None
        self.http = http or httpx.Client(
            timeout=settings.ibge_timeout,
            headers={"User-Agent": "dash-ibge/0.1", "Accept": "application/json"},
            follow_redirects=True,
            limits=httpx.Limits(max_connections=8, max_keepalive_connections=4),
        )

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> IbgeClient:
        from dash_ibge.cache.store import open_cache

        settings = settings or get_settings()
        return cls(settings, open_cache(settings))

    def close(self) -> None:
        if self._owns_http:
            self.http.close()
        close = getattr(self.cache, "close", None)
        if close:
            close()

    def __enter__(self) -> IbgeClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def agregado(self, query: AggregateQuery) -> object:
        url = build_agregado_url(
            self.settings.ibge_base_url,
            query.agregado,
            query.periodos,
            query.variaveis,
            query.localidades,
            query.classificacao,
        )
        cached = self.cache.get(url)
        if cached is not None:
            return cached
        try:
            response = self.http.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise IbgeError(f"Falha ao consultar o agregado {query.agregado} ({query.name}): {exc}") from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise IbgeError(f"Resposta inválida do agregado {query.agregado}.") from exc
        self.cache.set(url, payload, self.settings.cache_ttl_seconds)
        return payload
