from __future__ import annotations

import polars as pl

# Centroides aproximados, só para posicionar o gráfico. Não são limites territoriais.
_UFS: tuple[tuple[str, str, str, str, str, float, float], ...] = (
    ("11", "RO", "Rondônia", "1", "Norte", -10.83, -63.34),
    ("12", "AC", "Acre", "1", "Norte", -9.02, -70.81),
    ("13", "AM", "Amazonas", "1", "Norte", -3.47, -65.10),
    ("14", "RR", "Roraima", "1", "Norte", 1.99, -61.33),
    ("15", "PA", "Pará", "1", "Norte", -3.79, -52.48),
    ("16", "AP", "Amapá", "1", "Norte", 1.41, -51.77),
    ("17", "TO", "Tocantins", "1", "Norte", -10.17, -48.29),
    ("21", "MA", "Maranhão", "2", "Nordeste", -5.42, -45.44),
    ("22", "PI", "Piauí", "2", "Nordeste", -7.72, -42.73),
    ("23", "CE", "Ceará", "2", "Nordeste", -5.20, -39.53),
    ("24", "RN", "Rio Grande do Norte", "2", "Nordeste", -5.81, -36.59),
    ("25", "PB", "Paraíba", "2", "Nordeste", -7.12, -36.72),
    ("26", "PE", "Pernambuco", "2", "Nordeste", -8.38, -37.86),
    ("27", "AL", "Alagoas", "2", "Nordeste", -9.57, -36.78),
    ("28", "SE", "Sergipe", "2", "Nordeste", -10.57, -37.45),
    ("29", "BA", "Bahia", "2", "Nordeste", -13.29, -41.71),
    ("31", "MG", "Minas Gerais", "3", "Sudeste", -18.51, -44.55),
    ("32", "ES", "Espírito Santo", "3", "Sudeste", -19.57, -40.66),
    ("33", "RJ", "Rio de Janeiro", "3", "Sudeste", -22.25, -42.66),
    ("35", "SP", "São Paulo", "3", "Sudeste", -22.19, -48.79),
    ("41", "PR", "Paraná", "4", "Sul", -24.89, -51.55),
    ("42", "SC", "Santa Catarina", "4", "Sul", -27.45, -50.95),
    ("43", "RS", "Rio Grande do Sul", "4", "Sul", -30.17, -53.50),
    ("50", "MS", "Mato Grosso do Sul", "5", "Centro-Oeste", -20.51, -54.54),
    ("51", "MT", "Mato Grosso", "5", "Centro-Oeste", -12.64, -55.42),
    ("52", "GO", "Goiás", "5", "Centro-Oeste", -15.93, -49.84),
    ("53", "DF", "Distrito Federal", "5", "Centro-Oeste", -15.78, -47.93),
)


def territory_frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "localidade_id": [item[0] for item in _UFS],
            "sigla": [item[1] for item in _UFS],
            "nome_uf": [item[2] for item in _UFS],
            "regiao_id": [item[3] for item in _UFS],
            "regiao": [item[4] for item in _UFS],
            "lat": [item[5] for item in _UFS],
            "lon": [item[6] for item in _UFS],
        }
    )


def sigla_por_id() -> dict[str, str]:
    return {item[0]: item[1] for item in _UFS}


def id_por_sigla() -> dict[str, str]:
    return {item[1]: item[0] for item in _UFS}
