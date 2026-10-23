from __future__ import annotations

import polars as pl

CLASS_COLUMNS = {
    "1": "situacao_domicilio",
    "2": "sexo",
    "3": "especie",
    "58": "grupo_idade",
    "86": "cor_ou_raca",
    "286": "forma_declaracao_idade",
    "287": "idade",
}

OBSERVATION_SCHEMA: dict[str, pl.DataType] = {
    "agregado_id": pl.Utf8,
    "variavel_id": pl.Utf8,
    "variavel": pl.Utf8,
    "unidade": pl.Utf8,
    "localidade_id": pl.Utf8,
    "localidade_nome": pl.Utf8,
    "nivel_id": pl.Utf8,
    "nivel_nome": pl.Utf8,
    "periodo": pl.Utf8,
    "valor": pl.Utf8,
    "valor_num": pl.Float64,
    "sexo": pl.Utf8,
    "sexo_id": pl.Utf8,
    "idade": pl.Utf8,
    "idade_id": pl.Utf8,
    "cor_ou_raca": pl.Utf8,
    "cor_ou_raca_id": pl.Utf8,
    "situacao_domicilio": pl.Utf8,
    "situacao_domicilio_id": pl.Utf8,
    "grupo_idade": pl.Utf8,
    "grupo_idade_id": pl.Utf8,
    "especie": pl.Utf8,
    "especie_id": pl.Utf8,
    "forma_declaracao_idade": pl.Utf8,
    "forma_declaracao_idade_id": pl.Utf8,
}

_MISSING = {"", "-", "--", "...", "..", "X", "A", "N/A", "ND", "null", "None"}


def to_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if text in _MISSING:
        return None
    text = text.replace(" ", "")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def empty_observations() -> pl.DataFrame:
    return pl.DataFrame(schema=OBSERVATION_SCHEMA)


def parse_agregados(payload: object, agregado_id: str) -> pl.DataFrame:
    """Achata o JSON da API v3 de agregados em uma observação por localidade e período."""
    if not isinstance(payload, list):
        return empty_observations()

    rows: list[dict[str, object]] = []
    for variable in payload:
        if not isinstance(variable, dict):
            continue
        variable_id = str(variable.get("id", ""))
        variable_name = str(variable.get("variavel") or "")
        unit = str(variable.get("unidade") or "")
        for result in variable.get("resultados") or []:
            classes = _blank_classes()
            for classification in result.get("classificacoes") or []:
                column = CLASS_COLUMNS.get(str(classification.get("id")))
                category = classification.get("categoria") or {}
                if not column or not isinstance(category, dict) or not category:
                    continue
                category_id, category_name = next(iter(category.items()))
                classes[column] = str(category_name)
                classes[f"{column}_id"] = str(category_id)
            for series in result.get("series") or []:
                locality = series.get("localidade") or {}
                level = locality.get("nivel") or {}
                points = series.get("serie") or {}
                if not isinstance(points, dict):
                    continue
                for period, raw_value in points.items():
                    row: dict[str, object] = {
                        "agregado_id": str(agregado_id),
                        "variavel_id": variable_id,
                        "variavel": variable_name,
                        "unidade": unit,
                        "localidade_id": str(locality.get("id", "")),
                        "localidade_nome": str(locality.get("nome") or ""),
                        "nivel_id": str((level or {}).get("id", "")),
                        "nivel_nome": str((level or {}).get("nome") or ""),
                        "periodo": str(period),
                        "valor": None if raw_value is None else str(raw_value),
                        "valor_num": to_float(raw_value),
                    }
                    row.update(classes)
                    rows.append(row)

    if not rows:
        return empty_observations()
    frame = pl.DataFrame(rows)
    for column, dtype in OBSERVATION_SCHEMA.items():
        if column not in frame.columns:
            frame = frame.with_columns(pl.lit(None, dtype=dtype).alias(column))
    return frame.select(list(OBSERVATION_SCHEMA)).with_columns(
        pl.col("valor_num").cast(pl.Float64, strict=False)
    )


def _blank_classes() -> dict[str, str | None]:
    values: dict[str, str | None] = {}
    for column in CLASS_COLUMNS.values():
        values[column] = None
        values[f"{column}_id"] = None
    return values
