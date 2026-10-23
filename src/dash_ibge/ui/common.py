from __future__ import annotations

import plotly.graph_objects as go

from dash_ibge.formatting import fmt_num, fmt_pct, fmt_people
from dash_ibge.ui.theme import COLORWAY

__all__ = ["apply_layout", "footer", "header", "show_errors", "fmt_num", "fmt_pct", "fmt_people"]


def header(title: str, subtitle: str) -> None:
    import streamlit as st

    st.markdown(
        f"<div class='page-head'><h1>{title}</h1><p>{subtitle}</p></div>",
        unsafe_allow_html=True,
    )


def show_errors(errors: list[str]) -> None:
    import streamlit as st

    if not errors:
        return
    joined = "\n".join(f"- {error}" for error in errors)
    st.warning("Parte das tabelas do IBGE não entrou nesta leitura.\n\n" + joined)


def footer(text: str) -> None:
    import streamlit as st

    st.markdown(f"<p class='note'>{text}</p>", unsafe_allow_html=True)


def apply_layout(fig: go.Figure, height: int = 440) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=48, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Source Sans 3, sans-serif", color="#1c2834", size=13),
        colorway=COLORWAY,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        separators=",.",
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="#e6e0d4", zeroline=False)
    return fig
