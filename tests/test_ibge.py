from __future__ import annotations

import polars as pl

from dash_ibge.ibge.client import build_agregado_url
from dash_ibge.ibge.parse import parse_agregados, to_float


def test_numeros_com_marcadores_ausentes_e_decimais():
    assert to_float("-") is None
    assert to_float("...") is None
    assert to_float("366.97") == 366.97
    assert to_float("1.234,5") == 1234.5
    assert to_float("1,234.5") == 1234.5


def test_url_preserva_colchetes_e_pipe():
    url = build_agregado_url(
        "https://servicodados.ibge.gov.br/api/v3",
        "9543",
        ("2022",),
        ("2513",),
        "N1[1]|N3[all]",
        "2[6794,4,5]|86[95251]",
    )
    assert "localidades=N1[1]|N3[all]" in url
    assert "classificacao=2[6794,4,5]|86[95251]" in url
    assert "%5B" not in url


def test_parse_separa_categorias_e_converte_valor():
    payload = [
        {
            "id": "93",
            "variavel": "População residente",
            "unidade": "Pessoas",
            "resultados": [
                {
                    "classificacoes": [
                        {"id": "1", "nome": "Situação do domicílio", "categoria": {"1": "Urbana"}}
                    ],
                    "series": [
                        {
                            "localidade": {
                                "id": "33",
                                "nivel": {"id": "N3", "nome": "Unidade da Federação"},
                                "nome": "Rio de Janeiro",
                            },
                            "serie": {"2022": "16000000", "2010": "-"},
                        }
                    ],
                }
            ],
        }
    ]
    frame = parse_agregados(payload, "9923")
    assert frame.height == 2
    urbana = frame.filter(pl.col("periodo") == "2022")
    assert urbana.get_column("situacao_domicilio").item() == "Urbana"
    assert urbana.get_column("valor_num").item() == 16_000_000
    assert frame.filter(pl.col("periodo") == "2010").get_column("valor_num").item() is None
