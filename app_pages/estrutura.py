from __future__ import annotations

import polars as pl
import streamlit as st

from dash_ibge.ibge.catalog import AGE_ORDER
from dash_ibge.ui.charts import bar, grouped, pyramid
from dash_ibge.ui.common import footer, header, show_errors
from dash_ibge.ui.loaders import carregar_painel

header("Estrutura da população", "Idade, sexo, alfabetização e cor ou raça no Censo de 2022.")
painel = carregar_painel()
show_errors(painel.erros)

if painel.idades.is_empty():
    st.info("A pirâmide etária não chegou nesta leitura.")
else:
    places = {"Brasil": painel.idades.filter(pl.col("nivel_id") == "N1")}
    if not painel.unidades.is_empty():
        for row in painel.unidades.sort("sigla").iter_rows(named=True):
            places[f"{row['sigla']} · {row['nome']}"] = painel.idades.filter(
                (pl.col("nivel_id") == "N3") & (pl.col("localidade_id") == row["localidade_id"])
            )
    choice = st.selectbox("Recorte da pirâmide", list(places))
    subset = places[choice]
    if subset.is_empty():
        st.info("Esse recorte não tem grupos de idade.")
    else:
        labels = (
            subset.select("idade_id", "idade")
            .unique()
            .with_columns(pl.col("idade_id").replace_strict(AGE_ORDER, default=99).alias("ordem"))
            .sort("ordem")
            .get_column("idade")
            .to_list()
        )
        st.plotly_chart(pyramid(subset, labels), use_container_width=True)

columns = st.columns(2)
if not painel.unidades.is_empty() and "taxa_alfabetizacao" in painel.unidades.columns:
    sexo = painel.unidades.select(
        "sigla",
        "taxa_alfabetizacao_homens",
        "taxa_alfabetizacao_mulheres",
    ).unpivot(
        index="sigla",
        on=["taxa_alfabetizacao_homens", "taxa_alfabetizacao_mulheres"],
        variable_name="sexo",
        value_name="taxa",
    ).with_columns(pl.col("sexo").replace({"taxa_alfabetizacao_homens": "Homens", "taxa_alfabetizacao_mulheres": "Mulheres"}))
    with columns[0]:
        st.plotly_chart(grouped(sexo, "sigla", "taxa", "sexo", "Alfabetização de 15 anos ou mais (%)"), use_container_width=True)
    with columns[1]:
        ordem = painel.unidades.sort("indice_envelhecimento", descending=True)
        st.plotly_chart(bar(ordem, "sigla", "indice_envelhecimento", "Índice de envelhecimento", horizontal=True), use_container_width=True)

if not painel.cor.is_empty():
    st.subheader("Cor ou raça")
    nivel = st.radio("Recorte", ["Brasil", "UF"], horizontal=True)
    cor = painel.cor.filter(pl.col("variavel_id") == "1000093")
    if nivel == "Brasil":
        cor = cor.filter(pl.col("nivel_id") == "N1")
        chart = cor.with_columns(pl.col("periodo").alias("ano"))
        st.plotly_chart(grouped(chart, "cor_ou_raca", "valor_num", "ano", "Percentual por cor ou raça"), use_container_width=True)
    else:
        siglas = painel.unidades.sort("sigla").get_column("sigla").to_list() if not painel.unidades.is_empty() else []
        sigla = st.selectbox("UF", siglas)
        localidade = painel.unidades.filter(pl.col("sigla") == sigla).get_column("localidade_id").item()
        chart = cor.filter((pl.col("nivel_id") == "N3") & (pl.col("localidade_id") == localidade) & (pl.col("periodo") == "2022"))
        st.plotly_chart(bar(chart, "cor_ou_raca", "valor_num", f"Cor ou raça em 2022 · {sigla}"), use_container_width=True)

footer(
    "Pirâmide: tabela 9514, sexo e grupos de idade, declaração de idade no total. "
    "Alfabetização: tabela 9543. Cor ou raça: tabela 9605, percentuais de 2010 e 2022. "
    "Envelhecimento: tabela 9515."
)
