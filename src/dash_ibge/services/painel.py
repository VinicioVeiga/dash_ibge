from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import polars as pl

from dash_ibge.analytics.frames import age_frame, history_frame, municipal_wide, place_metrics, race_frame
from dash_ibge.config import Settings, get_settings
from dash_ibge.ibge.catalog import AggregateQuery, core_queries, municipal_query
from dash_ibge.ibge.client import IbgeClient
from dash_ibge.ibge.parse import empty_observations, parse_agregados


@dataclass
class CensoPainel:
    unidades: pl.DataFrame
    regioes: pl.DataFrame
    brasil: dict
    cor: pl.DataFrame
    situacao: pl.DataFrame
    idades: pl.DataFrame
    historia: pl.DataFrame
    erros: list[str] = field(default_factory=list)
    cache_backend: str = ""
    cache_detail: str = ""

    def to_cache(self) -> dict:
        return {
            "unidades": self.unidades.to_dicts(),
            "regioes": self.regioes.to_dicts(),
            "brasil": self.brasil,
            "cor": self.cor.to_dicts(),
            "situacao": self.situacao.to_dicts(),
            "idades": self.idades.to_dicts(),
            "historia": self.historia.to_dicts(),
            "erros": self.erros,
            "cache_backend": self.cache_backend,
            "cache_detail": self.cache_detail,
        }

    @classmethod
    def from_cache(cls, payload: dict) -> CensoPainel:
        return cls(
            unidades=_frame(payload.get("unidades") or []),
            regioes=_frame(payload.get("regioes") or []),
            brasil=dict(payload.get("brasil") or {}),
            cor=_frame(payload.get("cor") or []),
            situacao=_frame(payload.get("situacao") or []),
            idades=_frame(payload.get("idades") or []),
            historia=_frame(payload.get("historia") or []),
            erros=list(payload.get("erros") or []),
            cache_backend=str(payload.get("cache_backend") or ""),
            cache_detail=str(payload.get("cache_detail") or ""),
        )


@dataclass
class Municipios:
    locais: pl.DataFrame
    erros: list[str] = field(default_factory=list)

    def to_cache(self) -> dict:
        return {"locais": self.locais.to_dicts(), "erros": self.erros}

    @classmethod
    def from_cache(cls, payload: dict) -> Municipios:
        return cls(_frame(payload.get("locais") or []), list(payload.get("erros") or []))


class CensoService:
    def __init__(self, client: IbgeClient | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = client

    def load(self) -> CensoPainel:
        with self._open() as client:
            tables, erros = _fetch(client, core_queries())
            unidades = place_metrics(tables, "N3")
            regioes = place_metrics(tables, "N2")
            brasil_frame = place_metrics(tables, "N1")
            brasil = brasil_frame.to_dicts()[0] if brasil_frame.height else {}
            return CensoPainel(
                unidades=unidades,
                regioes=regioes,
                brasil=brasil,
                cor=race_frame(tables),
                situacao=tables.get("situacao", empty_observations()),
                idades=age_frame(tables),
                historia=history_frame(tables),
                erros=erros,
                cache_backend=client.cache.backend,
                cache_detail=client.cache.detail,
            )

    def load_municipios(self) -> Municipios:
        with self._open() as client:
            tables, erros = _fetch(client, (municipal_query(),))
            observations = tables.get("municipios", empty_observations())
            return Municipios(municipal_wide(observations), erros)

    def _open(self):
        if self._client is not None:
            return _NullClose(self._client)
        return IbgeClient.from_settings(self.settings)


class _NullClose:
    def __init__(self, client: IbgeClient) -> None:
        self.client = client

    def __enter__(self) -> IbgeClient:
        return self.client

    def __exit__(self, *exc: object) -> None:
        return None


def _fetch(client: IbgeClient, queries: tuple[AggregateQuery, ...]) -> tuple[dict[str, pl.DataFrame], list[str]]:
    frames: dict[str, pl.DataFrame] = {}
    errors: list[str] = []

    def run(query: AggregateQuery) -> tuple[str, pl.DataFrame, str | None]:
        try:
            payload = client.agregado(query)
            return query.name, parse_agregados(payload, query.agregado), None
        except Exception as exc:
            message = str(exc).splitlines()[0][:240]
            return query.name, empty_observations(), f"{query.descricao or query.name}: {message}"

    workers = min(4, len(queries))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for name, frame, error in pool.map(run, queries):
            frames[name] = frame
            if error:
                errors.append(error)
            elif frame.is_empty():
                errors.append(f"{name}: a API devolveu uma tabela vazia.")
    return frames, errors


def _frame(rows: list[dict]) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame()
    return pl.DataFrame(rows)
