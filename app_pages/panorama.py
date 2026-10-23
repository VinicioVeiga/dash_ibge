from __future__ import annotations

import polars as pl
import streamlit as st

from dash_ibge.analytics.stats import share
from dash_ibge.ui.charts import bar, bubbles, line
from dash_ibge.ui.common import footer, fmt_num, fmt_pct, fmt_people, header, show_errors
from dash_ibge.ui.loaders import carregar_painel

header(
    "Panorama do Censo",
    "População, território e ritmo de crescimento publicados pelo IBGE para 2022.",
)
painel = carregar_painel()
show_errors(painel.erros)
brasil = painel.brasil

if not brasil:
    st.info("Ainda não há o total do Brasil. Confira as mensagens acima ou use Atualizar dados.")
    st.stop()

populacao = brasil.get("populacao")
metrics = st.columns(4)
metrics[0].metric("População residente", fmt_people(populacao))
metrics[1].metric("Densidade", f"{fmt_num(brasil.get('densidade'))} hab/km²")
metrics[2].metric("Idade mediana", f"{fmt_num(brasil.get('idade_mediana'), 0)} anos")
metrics[3].metric("Crescimento geométrico", fmt_pct(brasil.get("taxa_crescimento")))

metrics = st.columns(4)
metrics[0].metric("Alfabetização 15+", fmt_pct(brasil.get("taxa_alfabetizacao")))
metrics[1].metric("Razão de sexo", fmt_num(brasil.get("razao_sexo")))
metrics[2].metric("Índice de envelhecimento", fmt_num(brasil.get("indice_envelhecimento")))
metrics[3].metric("Situação urbana", fmt_pct(brasil.get("pct_urbana")))

left, right = st.columns((1.35, 1))
with left:
    if not painel.unidades.is_empty():
        ranking = painel.unidades.sort("populacao", descending=True)
        st.plotly_chart(
            bar(ranking, "sigla", "populacao", "População residente por UF", horizontal=True),
            use_container_width=True,
        )
with right:
    if not painel.historia.is_empty():
        historia = painel.historia.with_columns(pl.col("periodo").cast(pl.Int32, strict=False))
        st.plotly_chart(
            line(historia, "periodo", "valor_num", "População recenseada do Brasil"),
            use_container_width=True,
        )
    elif not painel.regioes.is_empty():
        st.plotly_chart(
            bar(painel.regioes, "nome", "populacao", "População por grande região"),
            use_container_width=True,
        )

if not painel.unidades.is_empty() and {"lat", "lon", "densidade"}.issubset(painel.unidades.columns):
    st.plotly_chart(bubbles(painel.unidades), use_container_width=True)

if not painel.regioes.is_empty() and populacao:
    regiao = painel.regioes.with_columns(
        pl.Series(
            "participacao",
            [share(value, populacao) for value in painel.regioes.get_column("populacao").to_list()],
        )
    )
    st.plotly_chart(bar(regiao, "nome", "participacao", "Participação de cada região na população (%)"), use_container_width=True)

st.download_button(
    "Baixar indicadores das UFs",
    data=painel.unidades.write_csv() if not painel.unidades.is_empty() else "",
    file_name="censo_ufs_2022.csv",
    mime="text/csv",
)
footer(
    "Fontes: tabelas 4714, 4709, 9515, 9543, 9923 e 1209 da API de agregados do IBGE. "
    "A série histórica reúne censos com território e conceitos diferentes. "
    f"Cache desta leitura: {painel.cache_backend}."
)
