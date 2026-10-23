from __future__ import annotations

import math


def fmt_people(value: object) -> str:
    number = _number(value)
    if number is None:
        return "—"
    return f"{number:,.0f}".replace(",", ".")


def fmt_num(value: object, digits: int = 1) -> str:
    number = _number(value)
    if number is None:
        return "—"
    rendered = f"{number:,.{digits}f}"
    return rendered.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(value: object, digits: int = 1) -> str:
    rendered = fmt_num(value, digits)
    return rendered if rendered == "—" else f"{rendered}%"


def _number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number
