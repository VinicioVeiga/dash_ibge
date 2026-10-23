from __future__ import annotations

from dash_ibge.ai.corpus import Document
from dash_ibge.ai.jev import LocalJevBackend
from dash_ibge.ai.rag import RagPipeline
from dash_ibge.cache.store import MemoryCache
from dash_ibge.config import Settings


def _settings() -> Settings:
    return Settings(
        ibge_base_url="https://servicodados.ibge.gov.br/api/v3",
        ibge_timeout=5,
        redis_enabled=False,
        redis_url="redis://localhost:6379/0",
        cache_ttl_seconds=60,
        spark_enabled="0",
        llm_base_url="https://api.openai.com/v1",
        llm_api_key="",
        llm_model="gpt-4o-mini",
        jev_api_url="",
        jev_api_key="",
        jev_model="jev",
    )


def test_jev_local_aumenta_com_a_evidencia_e_fica_entre_zero_e_um():
    backend = LocalJevBackend()
    low, low_confidence = backend.noul(0.02, 0.0, 0.0)
    high, high_confidence = backend.noul(0.9, 0.8, 0.9)
    assert 0 <= low <= 1
    assert 0 <= high <= 1
    assert high > low
    assert 0 <= low_confidence <= 1
    assert 0 <= high_confidence <= 1
    accepted = backend.decide("selecao-contexto", "choice", 0.9, 0.8, 0.9)
    rejected = backend.decide("selecao-contexto", "choice", 0.02, 0.0, 0.0)
    realistic = backend.decide("selecao-contexto", "choice", 0.30, 0.6, 0.5)
    weak = backend.decide("selecao-contexto", "choice", 0.15, 0.0, 0.1)
    assert accepted.value == "aceitar"
    assert realistic.value == "aceitar"
    assert rejected.value == "recusar"
    assert weak.value == "recusar"


def test_rag_responde_com_o_numero_do_trecho_e_abstem_fora_do_censo():
    docs = [
        Document(
            "rr",
            "Roraima",
            "Roraima, Censo Demográfico de 2022. População residente: 636303 pessoas. Densidade demográfica: 2,85.",
        )
    ]
    pipeline = RagPipeline(docs, settings=_settings(), cache=MemoryCache(), jev=LocalJevBackend())
    answer = pipeline.answer("Qual a população residente de Roraima no Censo?")
    assert answer.abstained is False
    assert "636303" in answer.answer.replace(".", "").replace(",", "")
    assert any(item.name == "suficiencia" for item in answer.decisions)

    outside = pipeline.answer("Qual é a cotação do dólar hoje na bolsa?")
    assert outside.abstained is True
    assert outside.generator == "abstencao"
