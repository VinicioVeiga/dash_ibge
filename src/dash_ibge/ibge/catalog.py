from __future__ import annotations

from dataclasses import dataclass

# Grupos quinquenais da tabela 9514 (classificação 287), sem idades simples.
AGE_GROUP_IDS: tuple[str, ...] = (
    "93070",
    "93084",
    "93085",
    "93086",
    "93087",
    "93088",
    "93089",
    "93090",
    "93091",
    "93092",
    "93093",
    "93094",
    "93095",
    "93096",
    "93097",
    "93098",
    "49108",
    "49109",
    "60040",
    "60041",
    "6653",
)

AGE_ORDER: dict[str, int] = {age_id: index for index, age_id in enumerate(AGE_GROUP_IDS)}

HISTORICAL_PERIODS: tuple[str, ...] = (
    "1872",
    "1890",
    "1900",
    "1920",
    "1940",
    "1950",
    "1960",
    "1970",
    "1980",
    "1991",
    "2000",
    "2010",
    "2022",
)

GEO_ALL = "N1[1]|N2[all]|N3[all]"
PYRAMID_CLASS = "2[4,5]|287[" + ",".join(AGE_GROUP_IDS) + "]|286[113635]"
LITERACY_CLASS = "2[6794,4,5]|86[95251]|287[100362]"
RACE_CLASS = "86[95251,2776,2777,2778,2779,2780]"
HOUSEHOLD_CLASS = "3[59998]"
SITUATION_CLASS = "1[1,2]"
HISTORY_CLASS = "58[0]"

RACE_COLUMNS = {
    "2776": "pct_branca",
    "2777": "pct_preta",
    "2778": "pct_amarela",
    "2779": "pct_parda",
    "2780": "pct_indigena",
}


@dataclass(frozen=True)
class AggregateQuery:
    name: str
    agregado: str
    periodos: tuple[str, ...]
    variaveis: tuple[str, ...]
    localidades: str
    classificacao: str | None = None
    descricao: str = ""


def core_queries() -> tuple[AggregateQuery, ...]:
    """Consultas pequenas o bastante para o painel nacional, regional e por UF."""
    return (
        AggregateQuery(
            "territorio",
            "4714",
            ("2022",),
            ("93", "6318", "614"),
            GEO_ALL,
            descricao="População, área e densidade",
        ),
        AggregateQuery(
            "crescimento",
            "4709",
            ("2022",),
            ("5936", "10605"),
            GEO_ALL,
            descricao="Variação e taxa de crescimento geométrico",
        ),
        AggregateQuery(
            "estrutura",
            "9515",
            ("2022",),
            ("10612", "10613", "8845"),
            GEO_ALL,
            descricao="Envelhecimento, idade mediana e razão de sexo",
        ),
        AggregateQuery(
            "alfabetizacao",
            "9543",
            ("2022",),
            ("2513",),
            GEO_ALL,
            LITERACY_CLASS,
            "Taxa de alfabetização das pessoas de 15 anos ou mais",
        ),
        AggregateQuery(
            "cor",
            "9605",
            ("2010", "2022"),
            ("93", "1000093"),
            GEO_ALL,
            RACE_CLASS,
            "População por cor ou raça em 2010 e 2022",
        ),
        AggregateQuery(
            "situacao",
            "9923",
            ("2022",),
            ("93",),
            GEO_ALL,
            SITUATION_CLASS,
            "População urbana e rural",
        ),
        AggregateQuery(
            "idades",
            "9514",
            ("2022",),
            ("93",),
            GEO_ALL,
            PYRAMID_CLASS,
            "População por sexo e grupo de idade",
        ),
        AggregateQuery(
            "domicilios",
            "4711",
            ("2022",),
            ("617",),
            GEO_ALL,
            HOUSEHOLD_CLASS,
            "Domicílios particulares permanentes ocupados",
        ),
        AggregateQuery(
            "historia",
            "1209",
            HISTORICAL_PERIODS,
            ("606",),
            "N1[1]",
            HISTORY_CLASS,
            "População do Brasil nos censos desde 1872",
        ),
    )


def municipal_query() -> AggregateQuery:
    return AggregateQuery(
        "municipios",
        "4714",
        ("2022",),
        ("93", "6318", "614"),
        "N6[all]",
        descricao="População, área e densidade dos municípios",
    )
