from __future__ import annotations

import shutil
from dataclasses import dataclass

import polars as pl

from dash_ibge.config import Settings, get_settings
from dash_ibge.ibge.territory import sigla_por_id


@dataclass
class AggResult:
    frame: pl.DataFrame
    engine: str
    detail: str


def summarize_municipios(frame: pl.DataFrame, settings: Settings | None = None) -> AggResult:
    settings = settings or get_settings()
    prepared = _prepare(frame)
    mode = settings.spark_enabled
    wants_spark = mode in {"1", "true", "yes", "on"} or (mode == "auto" and _spark_ready())
    if wants_spark:
        try:
            return AggResult(_with_spark(prepared), "pyspark", "Agregação municipal executada no Spark local.")
        except Exception as exc:
            reason = str(exc).splitlines()[0][:180]
            if mode == "auto":
                detail = f"Spark não iniciou ({reason}). A agregação ficou no Polars."
            else:
                detail = f"SPARK_ENABLED={mode}, mas o Spark falhou ({reason}). A agregação ficou no Polars."
            return AggResult(_with_polars(prepared), "polars", detail)
    if mode in {"0", "false", "no", "off"}:
        detail = "SPARK_ENABLED desligado. Agregação municipal no Polars."
    else:
        detail = "PySpark ou Java não encontrados. Agregação municipal no Polars."
    return AggResult(_with_polars(prepared), "polars", detail)


def _prepare(frame: pl.DataFrame) -> pl.DataFrame:
    required = {"uf_id", "populacao", "densidade"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Colunas municipais ausentes: {', '.join(sorted(missing))}")
    return frame.with_columns(
        pl.col("populacao").cast(pl.Float64, strict=False),
        pl.col("densidade").cast(pl.Float64, strict=False),
        pl.col("uf_id").cast(pl.Utf8),
    )


def _with_polars(frame: pl.DataFrame) -> pl.DataFrame:
    summary = frame.group_by("uf_id").agg(
        pl.len().alias("municipios"),
        pl.col("populacao").sum().alias("populacao"),
        pl.col("densidade").mean().alias("densidade_media"),
        pl.col("populacao").max().alias("maior_municipio_pop"),
    )
    return _attach_sigla(summary).sort("populacao", descending=True)


def _with_spark(frame: pl.DataFrame) -> pl.DataFrame:
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F

    spark = (
        SparkSession.builder.master("local[2]")
        .appName("dash-ibge")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    data = spark.createDataFrame(frame.select("uf_id", "populacao", "densidade").to_dicts())
    summary = data.groupBy("uf_id").agg(
        F.count(F.lit(1)).alias("municipios"),
        F.sum("populacao").alias("populacao"),
        F.avg("densidade").alias("densidade_media"),
        F.max("populacao").alias("maior_municipio_pop"),
    )
    rows = [row.asDict() for row in summary.collect()]
    spark.stop()
    result = pl.DataFrame(rows).with_columns(
        pl.col("uf_id").cast(pl.Utf8),
        pl.col("municipios").cast(pl.Int64),
        pl.col("populacao").cast(pl.Float64),
        pl.col("densidade_media").cast(pl.Float64),
        pl.col("maior_municipio_pop").cast(pl.Float64),
    )
    return _attach_sigla(result).sort("populacao", descending=True)


def _attach_sigla(frame: pl.DataFrame) -> pl.DataFrame:
    siglas = pl.DataFrame({"uf_id": list(sigla_por_id()), "sigla": list(sigla_por_id().values())})
    return frame.join(siglas, on="uf_id", how="left")


def _spark_ready() -> bool:
    try:
        import pyspark  # noqa: F401
    except Exception:
        return False
    return shutil.which("java") is not None
