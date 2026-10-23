from __future__ import annotations

import numpy as np
import polars as pl
import streamlit as st

from dash_ibge.analytics.stats import index_against
from dash_ibge.ui.charts import bar, grouped
from dash_ibge.ui.common import footer, fmt_num, fmt_pct, fmt_people, header, show_errors
from dash_ibge.ui.loaders import carregar_painel

header("Território", "Compare unidades da federação com o total do Brasil como referência 100.")
painel = carregar_painel()
show_errors(painel.erros)
if painel.unidades.is_empty():
    st.info("Não há indicadores por UF nesta leitura.")
    st.stop()

options = painel.unidades.sort("sigla").get_column("sigla").to_list()
default = [sigla for sigla in ("SP", "RJ", "MG", "BA", "RS", "PA") if sigla in options]
escolha = st.multiselect("Unidades da federação", options, default=default)
if not escolha:
    st.info("Escolha ao menos uma UF.")
    st.stop()

selecao = painel.unidades.filter(pl.col("sigla").is_in(escolha)).sort("populacao", descending=True)
brasil = painel.brasil
columns = [
    ("populacao", "População"),
    ("densidade", "Densidade"),
    ("taxa_alfabetizacao", "Alfabetização"),
    ("indice_envelhecimento", "Envelhecimento"),
    ("pct_urbana", "Urbanização"),
    ("taxa_crescimento", "Crescimento"),
]
present = [(name, label) for name, label in columns if name in selecao.columns]

left, right = st.columns(2)
with left:
    st.plotly_chart(bar(selecao, "sigla", "densidade", "Densidade demográfica"), use_container_width=True)
with right:
    if "pct_urbana" in selecao.columns:
        urbano = selecao.select("sigla", "pop_urbana", "pop_rural").unpivot(
            index="sigla",
            on=["pop_urbana", "pop_rural"],
            variable_name="situacao",
            value_name="pessoas",
        ).with_columns(
            pl.col("situacao").replace({"pop_urbana": "Urbana", "pop_rural": "Rural"})
        )
        st.plotly_chart(grouped(urbano, "sigla", "pessoas", "situacao", "População urbana e rural"), use_container_width=True)

index_rows = []
for row in selecao.iter_rows(named=True):
    item = {"UF": f"{row['sigla']} · {row['nome']}"}
    for name, label in present:
        reference = brasil.get(name)
        values = index_against(np.array([row.get(name)]), float(reference) if reference is not None else np.nan)
        item[label] = None if np.isnan(values[0]) else round(float(values[0]), 1)
    index_rows.append(item)
st.subheader("Índice Brasil = 100")
st.dataframe(pl.DataFrame(index_rows), use_container_width=True, hide_index=True)

table = selecao.select(
    ["sigla", "nome", "regiao"]
    + [name for name, _label in present]
    + [name for name in ("area_km2", "moradores_por_domicilio") if name in selecao.columns]
)
st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
    column_config={
        "populacao": st.column_config.NumberColumn("População", format="%d"),
        "densidade": st.column_config.NumberColumn("Densidade", format="%.1f"),
        "taxa_alfabetizacao": st.column_config.NumberColumn("Alfabetização %", format="%.1f"),
        "pct_urbana": st.column_config.NumberColumn("Urbana %", format="%.1f"),
        "taxa_crescimento": st.column_config.NumberColumn("Crescimento %", format="%.2f"),
    },
)
st.caption(
    f"Brasil: {fmt_people(brasil.get('populacao'))} pessoas, "
    f"densidade {fmt_num(brasil.get('densidade'))}, "
    f"alfabetização {fmt_pct(brasil.get('taxa_alfabetizacao'))}."
)
footer("A urbanização usa a população urbana e rural da tabela 9923. O índice divide o valor da UF pelo valor do Brasil.")
