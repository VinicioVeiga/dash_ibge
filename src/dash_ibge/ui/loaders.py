from __future__ import annotations

import streamlit as st

from dash_ibge.services.painel import CensoPainel, CensoService, Municipios


@st.cache_data(ttl=1800, show_spinner=False)
def _painel_cache() -> dict:
    return CensoService().load().to_cache()


@st.cache_data(ttl=86400, show_spinner=False)
def _municipios_cache() -> dict:
    return CensoService().load_municipios().to_cache()


def carregar_painel() -> CensoPainel:
    with st.spinner("Consultando a API de agregados do IBGE..."):
        return CensoPainel.from_cache(_painel_cache())


def carregar_municipios() -> Municipios:
    with st.spinner("Lendo os municípios na tabela 4714. A primeira vez pode demorar."):
        return Municipios.from_cache(_municipios_cache())
