from __future__ import annotations

import time

import numpy as np
import polars as pl

from dash_ibge.analytics.clusters import cluster_ufs
from dash_ibge.analytics.frames import place_metrics
from dash_ibge.analytics.spark_agg import summarize_municipios
from dash_ibge.analytics.stats import correlation, index_against, log_histogram
from dash_ibge.cache.store import MemoryCache
from dash_ibge.config import Settings
from dash_ibge.ibge.parse import OBSERVATION_SCHEMA


def _settings(**changes) -> Settings:
    base = dict(
        ibge_base_url="https://servicodados.ibge.gov.br/api/v3",
        ibge_timeout=5,
        redis_enabled=False,
        redis_url="redis://localhost:6379/0",
        cache_ttl_seconds=30,
        spark_enabled="0",
        llm_base_url="https://api.openai.com/v1",
        llm_api_key="",
        llm_model="gpt-4o-mini",
        jev_api_url="",
        jev_api_key="",
        jev_model="jev",
    )
    base.update(changes)
    return Settings(**base)


def _obs(variavel: str, localidade: str, nivel: str, valor: float, **classes) -> dict:
    row = {name: None for name in OBSERVATION_SCHEMA}
    row.update(
        {
            "agregado_id": "1",
            "variavel_id": variavel,
            "variavel": variavel,
            "unidade": "",
            "localidade_id": localidade,
            "localidade_nome": "Rio de Janeiro" if localidade == "33" else "Brasil",
            "nivel_id": nivel,
            "nivel_nome": nivel,
            "periodo": "2022",
            "valor": str(valor),
            "valor_num": valor,
        }
    )
    row.update(classes)
    return row


def test_cache_em_memoria_respeita_o_prazo():
    cache = MemoryCache()
    cache.set("chave", {"valor": 7}, 1)
    assert cache.get("chave") == {"valor": 7}
    time.sleep(1.05)
    assert cache.get("chave") is None


def test_metricas_calculam_urbanizacao_e_sigla():
    rows = [
        _obs("93", "33", "N3", 100.0),
        _obs("6318", "33", "N3", 50.0),
        _obs("614", "33", "N3", 2.0),
        _obs("93", "33", "N3", 80.0, situacao_domicilio="Urbana", situacao_domicilio_id="1"),
        _obs("93", "33", "N3", 20.0, situacao_domicilio="Rural", situacao_domicilio_id="2"),
        _obs("617", "33", "N3", 40.0, especie="Particular permanente ocupado", especie_id="59998"),
    ]
    # As três primeiras linhas de população do território e da situação compartilham a variável 93.
    # A montagem separa as tabelas de origem, então o teste também separa.
    territorio = pl.DataFrame([rows[0], rows[1], rows[2]])
    situacao = pl.DataFrame([rows[3], rows[4]])
    domicilios = pl.DataFrame([rows[5]])
    unidades = place_metrics(
        {"territorio": territorio, "situacao": situacao, "domicilios": domicilios},
        "N3",
    )
    assert unidades.get_column("sigla").item() == "RJ"
    assert unidades.get_column("pct_urbana").item() == 80
    assert unidades.get_column("moradores_por_domicilio").item() == 2.5


def test_correlacao_e_histograma():
    matrix = np.array([[1.0, 2.0], [2.0, 4.0], [3.0, 6.0], [4.0, 8.0]])
    corr = correlation(matrix)
    assert corr.shape == (2, 2)
    assert corr[0, 1] > 0.99
    counts, edges = log_histogram(np.array([10, 100, 1000, 10000]))
    assert counts.sum() == 4
    assert edges[0] > 0
    assert index_against(np.array([50.0]), 25.0)[0] == 200


def test_grupos_separam_dois_perfis():
    rows = []
    for index in range(6):
        rows.append(
            {
                "sigla": f"A{index}",
                "nome": f"Alta {index}",
                "regiao": "Sul",
                "densidade": 400 + index,
                "taxa_alfabetizacao": 96,
                "pct_urbana": 92,
                "taxa_crescimento": 0.4,
            }
        )
    for index in range(6):
        rows.append(
            {
                "sigla": f"B{index}",
                "nome": f"Baixa {index}",
                "regiao": "Norte",
                "densidade": 4 + index,
                "taxa_alfabetizacao": 80,
                "pct_urbana": 55,
                "taxa_crescimento": 2.4,
            }
        )
    result = cluster_ufs(pl.DataFrame(rows), k=2)
    grupos = set(result.frame.get_column("grupo").to_list())
    assert grupos == {1, 2}
    assert result.frame.filter(pl.col("sigla").str.starts_with("A")).get_column("grupo").n_unique() == 1
    assert result.frame.filter(pl.col("sigla").str.starts_with("B")).get_column("grupo").n_unique() == 1


def test_agregacao_municipal_no_polars_quando_spark_esta_desligado():
    frame = pl.DataFrame(
        {
            "uf_id": ["33", "33", "35"],
            "populacao": [10.0, 5.0, 7.0],
            "densidade": [1.0, 2.0, 3.0],
        }
    )
    result = summarize_municipios(frame, _settings())
    assert result.engine == "polars"
    rio = result.frame.filter(pl.col("sigla") == "RJ")
    assert rio.get_column("municipios").item() == 2
    assert rio.get_column("populacao").item() == 15
