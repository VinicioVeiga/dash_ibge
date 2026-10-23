from __future__ import annotations

import polars as pl

from dash_ibge.ibge.catalog import RACE_COLUMNS
from dash_ibge.ibge.territory import territory_frame


def pull(
    frame: pl.DataFrame,
    variavel_id: str,
    column: str,
    nivel: str,
    filters: dict[str, str] | None = None,
    periodo: str | None = None,
) -> pl.DataFrame:
    if frame.is_empty():
        return pl.DataFrame(schema={"localidade_id": pl.Utf8, "localidade_nome": pl.Utf8, column: pl.Float64})
    out = frame.filter(
        (pl.col("variavel_id") == str(variavel_id)) & (pl.col("nivel_id") == nivel)
    )
    if periodo is not None:
        out = out.filter(pl.col("periodo") == str(periodo))
    for key, expected in (filters or {}).items():
        if key in out.columns:
            out = out.filter(pl.col(key) == str(expected))
    if out.is_empty():
        return pl.DataFrame(schema={"localidade_id": pl.Utf8, "localidade_nome": pl.Utf8, column: pl.Float64})
    return (
        out.select("localidade_id", "localidade_nome", pl.col("valor_num").alias(column))
        .unique(subset=["localidade_id"], keep="last")
    )


def _ensure_float(frame: pl.DataFrame, *columns: str) -> pl.DataFrame:
    missing = [pl.lit(None, dtype=pl.Float64).alias(column) for column in columns if column not in frame.columns]
    if not missing:
        return frame
    return frame.with_columns(missing)


def _join_metric(base: pl.DataFrame, metric: pl.DataFrame) -> pl.DataFrame:
    if metric.is_empty():
        return base
    extra = [column for column in metric.columns if column not in {"localidade_id", "localidade_nome"}]
    return base.join(metric.select(["localidade_id", *extra]), on="localidade_id", how="left")


def place_metrics(tables: dict[str, pl.DataFrame], nivel: str) -> pl.DataFrame:
    territorio = tables.get("territorio")
    if territorio is None or territorio.is_empty():
        return pl.DataFrame()
    base = pull(territorio, "93", "populacao", nivel)
    if base.is_empty():
        return base
    base = _join_metric(base, pull(territorio, "6318", "area_km2", nivel))
    base = _join_metric(base, pull(territorio, "614", "densidade", nivel))

    crescimento = tables.get("crescimento", territorio.clear())
    base = _join_metric(base, pull(crescimento, "5936", "variacao_absoluta_2010", nivel))
    base = _join_metric(base, pull(crescimento, "10605", "taxa_crescimento", nivel))

    estrutura = tables.get("estrutura", territorio.clear())
    base = _join_metric(base, pull(estrutura, "10612", "indice_envelhecimento", nivel))
    base = _join_metric(base, pull(estrutura, "10613", "idade_mediana", nivel))
    base = _join_metric(base, pull(estrutura, "8845", "razao_sexo", nivel))

    alfabetizacao = tables.get("alfabetizacao", territorio.clear())
    literacy_total = {"sexo_id": "6794", "cor_ou_raca_id": "95251", "idade_id": "100362"}
    base = _join_metric(
        base,
        pull(alfabetizacao, "2513", "taxa_alfabetizacao", nivel, literacy_total),
    )
    base = _join_metric(
        base,
        pull(alfabetizacao, "2513", "taxa_alfabetizacao_homens", nivel, {**literacy_total, "sexo_id": "4"}),
    )
    base = _join_metric(
        base,
        pull(alfabetizacao, "2513", "taxa_alfabetizacao_mulheres", nivel, {**literacy_total, "sexo_id": "5"}),
    )

    domicilios = tables.get("domicilios", territorio.clear())
    base = _join_metric(
        base,
        pull(domicilios, "617", "domicilios_ocupados", nivel, {"especie_id": "59998"}),
    )
    base = _ensure_float(base, "domicilios_ocupados")
    base = base.with_columns(
        pl.when(pl.col("domicilios_ocupados") > 0)
        .then(pl.col("populacao") / pl.col("domicilios_ocupados"))
        .otherwise(None)
        .alias("moradores_por_domicilio")
    )

    situacao = tables.get("situacao", territorio.clear())
    urbana = pull(situacao, "93", "pop_urbana", nivel, {"situacao_domicilio_id": "1"})
    rural = pull(situacao, "93", "pop_rural", nivel, {"situacao_domicilio_id": "2"})
    base = _join_metric(base, urbana)
    base = _join_metric(base, rural)
    base = _ensure_float(base, "pop_urbana", "pop_rural")
    base = base.with_columns(
        pl.when((pl.col("pop_urbana") + pl.col("pop_rural")) > 0)
        .then(pl.col("pop_urbana") / (pl.col("pop_urbana") + pl.col("pop_rural")) * 100)
        .otherwise(None)
        .alias("pct_urbana")
    )

    cor = tables.get("cor", territorio.clear())
    for category_id, column in RACE_COLUMNS.items():
        share = pull(
            cor,
            "1000093",
            column,
            nivel,
            {"cor_ou_raca_id": category_id},
            periodo="2022",
        )
        base = _join_metric(base, share)

    if nivel == "N3":
        base = base.join(territory_frame(), on="localidade_id", how="left")
        base = base.with_columns(
            pl.coalesce(pl.col("localidade_nome"), pl.col("nome_uf")).alias("nome"),
        )
    else:
        base = base.rename({"localidade_nome": "nome"})
    return base.sort("populacao", descending=True, nulls_last=True)


def age_frame(tables: dict[str, pl.DataFrame]) -> pl.DataFrame:
    idades = tables.get("idades")
    if idades is None or idades.is_empty():
        return pl.DataFrame()
    return idades.filter(
        (pl.col("variavel_id") == "93")
        & (pl.col("sexo_id").is_in(["4", "5"]))
        & pl.col("idade_id").is_not_null()
    )


def race_frame(tables: dict[str, pl.DataFrame]) -> pl.DataFrame:
    cor = tables.get("cor")
    if cor is None or cor.is_empty():
        return pl.DataFrame()
    return cor.filter(pl.col("cor_ou_raca_id") != "95251")


def history_frame(tables: dict[str, pl.DataFrame]) -> pl.DataFrame:
    historia = tables.get("historia")
    if historia is None or historia.is_empty():
        return pl.DataFrame()
    return historia.filter(pl.col("variavel_id") == "606").sort("periodo")


def municipal_wide(observations: pl.DataFrame) -> pl.DataFrame:
    if observations.is_empty():
        return pl.DataFrame()
    populacao = pull(observations, "93", "populacao", "N6")
    area = pull(observations, "6318", "area_km2", "N6")
    densidade = pull(observations, "614", "densidade", "N6")
    wide = _join_metric(populacao, area)
    wide = _join_metric(wide, densidade)
    return wide.with_columns(
        pl.col("localidade_id").str.zfill(7).str.slice(0, 2).alias("uf_id"),
        pl.col("localidade_nome").alias("nome"),
    )
