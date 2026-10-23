from __future__ import annotations

import polars as pl
import streamlit as st

from dash_ibge.analytics.clusters import cluster_ufs
from dash_ibge.ui.charts import heatmap, scatter
from dash_ibge.ui.common import footer, fmt_num, header, show_errors
from dash_ibge.ui.loaders import carregar_painel

header(
    "Modelos",
    "Os grupos reúnem UFs parecidas. São uma leitura descritiva, não uma tipologia do IBGE.",
)
painel = carregar_painel()
show_errors(painel.erros)
if painel.unidades.is_empty():
    st.info("Não há UFs suficientes para o modelo.")
    st.stop()

modo = st.radio("Número de grupos", ["Escolher pelo silhouette", "Definir"], horizontal=True)
k = None
if modo == "Definir":
    k = st.slider("Grupos", min_value=2, max_value=5, value=3)

try:
    resultado = cluster_ufs(painel.unidades, k=k)
except ValueError as exc:
    st.info(str(exc))
    st.stop()

resumo = st.columns(3)
resumo[0].metric("Grupos", str(resultado.k))
resumo[1].metric("Silhouette", fmt_num(resultado.silhouette, 3))
variancia = float(resultado.explained.sum()) * 100 if len(resultado.explained) else 0
resumo[2].metric("Variância nos dois eixos", fmt_num(variancia, 1) + "%")
if resultado.imputed:
    st.caption("Medianas preencheram buracos em: " + ", ".join(resultado.imputed) + ".")

st.plotly_chart(
    scatter(resultado.frame, "pca_1", "pca_2", "grupo", "sigla", "UFs nos dois primeiros componentes"),
    use_container_width=True,
)
st.plotly_chart(
    heatmap(resultado.correlation, resultado.labels_features, "Correlação entre indicadores padronizados"),
    use_container_width=True,
)

for grupo in range(1, resultado.k + 1):
    membros = resultado.frame.filter(pl.col("grupo") == grupo).get_column("sigla").to_list()
    st.markdown(f"**Grupo {grupo}** · {', '.join(membros)}")
    st.write(resultado.summaries[grupo - 1])

center = pl.DataFrame(
    resultado.centers,
    schema=resultado.labels_features,
).with_columns(pl.Series("grupo", list(range(1, resultado.k + 1))))
st.dataframe(center, use_container_width=True, hide_index=True)
st.caption("Silhouette por alternativa: " + ", ".join(f"{item}={score:.3f}" for item, score in resultado.silhouettes.items()))
footer(
    "K-means com variáveis padronizadas (scikit-learn) e componentes principais por decomposição de valores "
    "singulares (NumPy). O silhouette escolhe o número de grupos quando você não fixa um valor."
)
