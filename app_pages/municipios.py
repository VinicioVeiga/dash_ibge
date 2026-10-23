from __future__ import annotations

import plotly.graph_objects as go
import polars as pl
import streamlit as st

from dash_ibge.analytics.spark_agg import summarize_municipios
from dash_ibge.analytics.stats import log_histogram
from dash_ibge.ibge.territory import sigla_por_id
from dash_ibge.ui.charts import bar
from dash_ibge.ui.common import apply_layout, footer, fmt_people, header, show_errors
from dash_ibge.ui.loaders import carregar_municipios
from dash_ibge.ui.theme import COLORWAY

header("Municípios", "A leitura municipal usa a tabela 4714 e só começa quando você pede.")
if "municipios_ok" not in st.session_state:
    st.session_state.municipios_ok = False

if st.button("Carregar municípios", type="primary"):
    st.session_state.municipios_ok = True

if not st.session_state.municipios_ok:
    st.info("São 5.570 municípios. O resultado fica em cache por 24 horas.")
    st.stop()

carga = carregar_municipios()
show_errors(carga.erros)
if carga.locais.is_empty():
    st.info("A tabela municipal não foi carregada.")
    st.stop()

resumo = summarize_municipios(carga.locais)
st.caption(f"Motor da agregação por UF: {resumo.engine}. {resumo.detail}")

siglas = sorted(value for value in carga.locais.get_column("uf_id").unique().to_list())
nomes = sigla_por_id()
rotulos = [f"{nomes.get(code, code)} · {code}" for code in siglas]
escolha = st.selectbox("Unidade da federação", rotulos, index=rotulos.index("SP · 35") if "SP · 35" in rotulos else 0)
uf_id = escolha.split("·")[-1].strip()
parte = carga.locais.filter(pl.col("uf_id") == uf_id).sort("populacao", descending=True, nulls_last=True)

totais = st.columns(3)
totais[0].metric("Municípios", f"{parte.height}")
totais[1].metric("População somada", fmt_people(parte.get_column("populacao").sum()))
totais[2].metric("Maior município", parte.item(0, "nome") if parte.height else "—")

busca = st.text_input("Buscar município")
visivel = parte
if busca.strip():
    visivel = parte.filter(pl.col("nome").str.to_lowercase().str.contains(busca.strip().lower(), literal=True))

st.plotly_chart(bar(visivel.head(15), "nome", "populacao", "Quinze maiores populações", horizontal=True), use_container_width=True)

counts, edges = log_histogram(parte.get_column("populacao").to_numpy())
if counts.size:
    labels = [f"{edges[i]:,.0f}–{edges[i + 1]:,.0f}".replace(",", ".") for i in range(len(counts))]
    fig = go.Figure(go.Bar(x=labels, y=counts, marker_color=COLORWAY[0]))
    fig.update_layout(title="Distribuição da população municipal em escala logarítmica")
    st.plotly_chart(apply_layout(fig, 380), use_container_width=True)

st.dataframe(
    visivel.select("nome", "populacao", "area_km2", "densidade"),
    use_container_width=True,
    hide_index=True,
    column_config={
        "populacao": st.column_config.NumberColumn("População", format="%d"),
        "area_km2": st.column_config.NumberColumn("Área km²", format="%.1f"),
        "densidade": st.column_config.NumberColumn("Densidade", format="%.1f"),
    },
)

with st.expander("Soma municipal por UF"):
    st.dataframe(resumo.frame, use_container_width=True, hide_index=True)

footer("População, área e densidade saem da mesma tabela 4714, nível municipal. A soma por UF deve se aproximar do total da UF.")
