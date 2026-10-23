from __future__ import annotations

import unicodedata
from dataclasses import dataclass

import polars as pl

from dash_ibge.formatting import fmt_num, fmt_people


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    text: str


def documents_from_frames(
    unidades: pl.DataFrame,
    regioes: pl.DataFrame,
    brasil: dict,
    historia: pl.DataFrame,
    idades: pl.DataFrame,
) -> list[Document]:
    docs = list(GLOSSARY)
    if not unidades.is_empty():
        for row in unidades.iter_rows(named=True):
            docs.append(_place_document(row, "uf"))
    if not regioes.is_empty():
        for row in regioes.iter_rows(named=True):
            docs.append(_place_document(row, "regiao"))
    if brasil:
        docs.append(_place_document(brasil, "brasil"))
    if not historia.is_empty():
        docs.append(_history_document(historia))
    if not idades.is_empty():
        docs.append(_pyramid_document(idades))
    return [doc for doc in docs if doc.text.strip()]


def _place_document(row: dict, kind: str) -> Document:
    nome = row.get("nome") or row.get("localidade_nome") or "recorte"
    sigla = row.get("sigla") or ""
    title = f"{nome} ({sigla})" if sigla else str(nome)
    if kind == "brasil":
        title = "Brasil"
        doc_id = "brasil"
    elif kind == "regiao":
        doc_id = f"regiao-{row.get('localidade_id')}"
    else:
        doc_id = f"uf-{sigla or row.get('localidade_id')}"
    lines = [
        f"{title}, Censo Demográfico de 2022, dados agregados do IBGE.",
        _line("População residente", row.get("populacao"), people=True),
        _line("Área territorial em quilômetros quadrados", row.get("area_km2")),
        _line("Densidade demográfica em habitantes por quilômetro quadrado", row.get("densidade")),
        _line("Variação absoluta da população residente compatibilizada desde 2010", row.get("variacao_absoluta_2010"), people=True),
        _line("Taxa de crescimento geométrico em percentual", row.get("taxa_crescimento"), digits=2),
        _line("Índice de envelhecimento", row.get("indice_envelhecimento")),
        _line("Idade mediana em anos", row.get("idade_mediana")),
        _line("Razão de sexo, homens para cada 100 mulheres", row.get("razao_sexo")),
        _line("Taxa de alfabetização das pessoas de 15 anos ou mais, em percentual", row.get("taxa_alfabetizacao")),
        _line("Taxa de alfabetização dos homens de 15 anos ou mais", row.get("taxa_alfabetizacao_homens")),
        _line("Taxa de alfabetização das mulheres de 15 anos ou mais", row.get("taxa_alfabetizacao_mulheres")),
        _line("População em situação urbana", row.get("pop_urbana"), people=True),
        _line("População em situação rural", row.get("pop_rural"), people=True),
        _line("Percentual da população em situação urbana", row.get("pct_urbana")),
        _line("Domicílios particulares permanentes ocupados", row.get("domicilios_ocupados"), people=True),
        _line("Pessoas residentes por domicílio particular permanente ocupado", row.get("moradores_por_domicilio")),
        _line("Percentual de pessoas de cor ou raça branca em 2022", row.get("pct_branca")),
        _line("Percentual de pessoas de cor ou raça preta em 2022", row.get("pct_preta")),
        _line("Percentual de pessoas de cor ou raça amarela em 2022", row.get("pct_amarela")),
        _line("Percentual de pessoas de cor ou raça parda em 2022", row.get("pct_parda")),
        _line("Percentual de pessoas indígenas em 2022", row.get("pct_indigena")),
    ]
    if row.get("regiao") and kind == "uf":
        lines.insert(1, f"Grande região: {row['regiao']}.")
    text = " ".join(line for line in lines if line)
    return Document(doc_id, title, text)


def _history_document(frame: pl.DataFrame) -> Document:
    parts = []
    for row in frame.sort("periodo").iter_rows(named=True):
        if row.get("valor_num") is None:
            continue
        parts.append(f"{row['periodo']}: {fmt_people(row['valor_num'])}")
    text = (
        "Evolução da população recenseada do Brasil desde 1872, série histórica da tabela 1209, total nacional. "
        + "; ".join(parts)
        + ". Os censos antigos não são diretamente comparáveis em território e conceito."
    )
    return Document("historia-brasil", "Série histórica da população", text)


def _pyramid_document(frame: pl.DataFrame) -> Document:
    brasil = frame.filter(pl.col("nivel_id") == "N1")
    if brasil.is_empty():
        return Document("piramide-brasil", "Pirâmide etária", "")
    homens = brasil.filter(pl.col("sexo_id") == "4").select(pl.col("valor_num").sum()).item()
    mulheres = brasil.filter(pl.col("sexo_id") == "5").select(pl.col("valor_num").sum()).item()
    text = (
        "Pirâmide etária do Brasil no Censo 2022, tabela 9514, grupos de idade e sexo, "
        f"forma de declaração da idade no total. Homens: {fmt_people(homens)}. "
        f"Mulheres: {fmt_people(mulheres)}."
    )
    return Document("piramide-brasil", "Estrutura etária do Brasil", text)


def _line(label: str, value: object, people: bool = False, digits: int = 1) -> str:
    if value is None:
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    rendered = fmt_people(number) if people else fmt_num(number, digits)
    return f"{label}: {rendered}."


def fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    without = "".join(char for char in normalized if not unicodedata.combining(char))
    return without.lower()


GLOSSARY: tuple[Document, ...] = (
    Document(
        "gloss-censo",
        "Censo Demográfico",
        "O Censo Demográfico é o recenseamento da população e dos domicílios feito pelo IBGE. "
        "O mais recente foi realizado em 2022, com data de referência em agosto. Este painel lê "
        "resultados já agregados na API do IBGE e não os microdados.",
    ),
    Document(
        "gloss-envelhecimento",
        "Índice de envelhecimento",
        "O índice de envelhecimento publicado na tabela 9515 relaciona o contingente de pessoas idosas "
        "ao de crianças e jovens. O valor exibido é o da API, em forma de razão, sem recálculo local. "
        "Uma razão mais alta indica uma estrutura etária mais envelhecida.",
    ),
    Document(
        "gloss-sexo",
        "Razão de sexo",
        "A razão de sexo da tabela 9515 expressa quantos homens existem para cada 100 mulheres. "
        "Um valor abaixo de 100 indica mais mulheres do que homens na população residente.",
    ),
    Document(
        "gloss-alfabetizacao",
        "Taxa de alfabetização",
        "A taxa de alfabetização da tabela 9543 considera pessoas de 15 anos ou mais de idade. "
        "O painel mostra o total e o recorte por sexo, com cor ou raça e idade no total da classificação.",
    ),
    Document(
        "gloss-cor",
        "Cor ou raça",
        "A cor ou raça no Censo é declarada pela pessoa moradora. As categorias acompanhadas aqui são "
        "branca, preta, amarela, parda e indígena, na tabela 9605, para 2010 e 2022. Os percentuais "
        "vêm da variável de percentual do total geral.",
    ),
    Document(
        "gloss-situacao",
        "Situação do domicílio",
        "A situação do domicílio na tabela 9923 separa a população residente em urbana e rural, "
        "conforme a classificação do IBGE para o Censo 2022.",
    ),
    Document(
        "gloss-densidade",
        "Densidade demográfica",
        "A densidade demográfica da tabela 4714 é a população residente dividida pela área da unidade "
        "territorial, em habitantes por quilômetro quadrado, no ano de 2022.",
    ),
    Document(
        "gloss-crescimento",
        "Crescimento geométrico",
        "A taxa de crescimento geométrico da tabela 4709 descreve o ritmo médio de variação da "
        "população residente entre o Censo de 2010, em base compatibilizada, e o Censo de 2022.",
    ),
)
