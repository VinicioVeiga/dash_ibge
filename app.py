from __future__ import annotations

import streamlit as st

from dash_ibge import __version__
from dash_ibge.services.status import probe_stack
from dash_ibge.ui.theme import CSS

st.set_page_config(
    page_title="Censo IBGE",
    page_icon="▣",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CSS, unsafe_allow_html=True)

pages = [
    st.Page("app_pages/panorama.py", title="Panorama", default=True),
    st.Page("app_pages/territorio.py", title="Território"),
    st.Page("app_pages/estrutura.py", title="Estrutura"),
    st.Page("app_pages/municipios.py", title="Municípios"),
    st.Page("app_pages/modelos.py", title="Modelos"),
    st.Page("app_pages/assistente.py", title="Assistente"),
    st.Page("app_pages/integracoes.py", title="Integrações"),
]

with st.sidebar:
    st.markdown("### Censo Demográfico")
    st.caption(f"Agregados do IBGE · v{__version__}")
    status = probe_stack()
    st.caption(f"Cache: {status['redis']['backend']}")
    st.caption(f"Spark: {status['spark']['estado']}")
    st.caption(f"Jev: {status['jev']['backend']}")
    st.caption("LLM: configurado" if status["llm"]["configurado"] else "LLM: extrativo")
    if st.button("Atualizar dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.navigation(pages).run()
