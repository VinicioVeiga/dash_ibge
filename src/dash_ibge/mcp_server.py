from __future__ import annotations

import logging
import sys

import polars as pl

from dash_ibge.ai.corpus import documents_from_frames
from dash_ibge.ai.rag import RagPipeline
from dash_ibge.analytics.clusters import FEATURE_LABELS
from dash_ibge.services.painel import CensoPainel, CensoService
from dash_ibge.services.status import probe_stack

_painel: CensoPainel | None = None
_pipeline: RagPipeline | None = None


def _load() -> CensoPainel:
    global _painel, _pipeline
    if _painel is None:
        _painel = CensoService().load()
        _pipeline = RagPipeline(
            documents_from_frames(
                _painel.unidades,
                _painel.regioes,
                _painel.brasil,
                _painel.historia,
                _painel.idades,
            )
        )
    return _painel


def _row_by_sigla(sigla: str) -> dict:
    painel = _load()
    code = sigla.strip().upper()
    if painel.unidades.is_empty() or "sigla" not in painel.unidades.columns:
        raise ValueError("Os indicadores por UF ainda não estão disponíveis.")
    found = painel.unidades.filter(pl.col("sigla") == code)
    if found.is_empty():
        raise ValueError(f"UF desconhecida: {sigla}. Use a sigla, por exemplo RJ.")
    return found.to_dicts()[0]


def status_integracoes() -> dict:
    """Informa Redis, Spark, LLM, Jev e o endereço da API do IBGE."""
    base = probe_stack()
    painel = _load()
    base["erros_carga"] = painel.erros
    base["cache_da_carga"] = {"backend": painel.cache_backend, "detalhe": painel.cache_detail}
    return base


def listar_ufs() -> list[dict]:
    """Lista as unidades da federação com população, densidade e região."""
    painel = _load()
    if painel.unidades.is_empty():
        return []
    columns = [name for name in ("sigla", "nome", "regiao", "populacao", "densidade", "pct_urbana") if name in painel.unidades.columns]
    return painel.unidades.select(columns).to_dicts()


def indicadores_uf(sigla: str) -> dict:
    """Retorna os indicadores do Censo 2022 de uma UF pela sigla."""
    return _row_by_sigla(sigla)


def ranking(indicador: str, n: int = 10, ordem: str = "desc") -> list[dict]:
    """Ordena as UFs por um indicador. Indicadores: populacao, densidade, taxa_alfabetizacao, indice_envelhecimento, pct_urbana, taxa_crescimento."""
    painel = _load()
    column = indicador.strip()
    allowed = set(FEATURE_LABELS) | {"populacao", "area_km2"}
    if column not in allowed or column not in painel.unidades.columns:
        raise ValueError(f"Indicador indisponível: {indicador}.")
    limit = max(1, min(int(n), 27))
    ordered = painel.unidades.sort(column, descending=ordem.strip().lower() != "asc", nulls_last=True)
    keep = [name for name in ("sigla", "nome", "regiao", column) if name in ordered.columns]
    return ordered.select(keep).head(limit).to_dicts()


def responder(pergunta: str) -> dict:
    """Responde uma pergunta sobre o Censo com RAG, decisões Jev e LLM se estiver configurado."""
    _load()
    if _pipeline is None:
        raise RuntimeError("O índice do RAG não foi montado.")
    result = _pipeline.answer(pergunta)
    return {
        "resposta": result.answer,
        "absteve": result.abstained,
        "gerador": result.generator,
        "fontes": [doc.title for doc in result.passages],
        "decisoes": [
            {
                "nome": item.name,
                "tipo": item.kind,
                "valor": item.value,
                "confianca": item.confidence,
                "backend": item.backend,
                "detalhe": item.detail,
            }
            for item in result.decisions
        ],
    }


def main() -> None:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(name)s %(message)s")
    try:
        from mcp.server.mcpserver import MCPServer
    except Exception as exc:  # pragma: no cover - depende do pacote instalado
        raise SystemExit(f"O pacote mcp não está instalado: {exc}") from exc

    server = MCPServer("ibge-censo")
    server.add_tool(status_integracoes)
    server.add_tool(listar_ufs)
    server.add_tool(indicadores_uf)
    server.add_tool(ranking)
    server.add_tool(responder)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
