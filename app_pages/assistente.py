from __future__ import annotations

import html

import streamlit as st

from dash_ibge.ai.corpus import documents_from_frames
from dash_ibge.ai.rag import RagPipeline
from dash_ibge.ui.common import footer, header, show_errors
from dash_ibge.ui.loaders import carregar_painel

header(
    "Assistente",
    "A resposta sai dos indicadores carregados. As decisões de Jev dizem se o contexto basta e se a resposta fica.",
)
painel = carregar_painel()
show_errors(painel.erros)
documentos = documents_from_frames(
    painel.unidades,
    painel.regioes,
    painel.brasil,
    painel.historia,
    painel.idades,
)
pipeline = RagPipeline(documentos)

exemplos = [
    "Qual é a população e a densidade do Rio de Janeiro?",
    "O que é a razão de sexo?",
    "Quais UFs do Nordeste têm alfabetização mais baixa?",
    "Como evoluiu a população do Brasil desde 1872?",
]
if "pergunta_censo" not in st.session_state:
    st.session_state.pergunta_censo = exemplos[0]

cols = st.columns(len(exemplos))
for column, exemplo in zip(cols, exemplos):
    if column.button(exemplo, use_container_width=True):
        st.session_state.pergunta_censo = exemplo
        st.rerun()

pergunta = st.text_area("Pergunta", key="pergunta_censo", height=90)
if st.button("Perguntar", type="primary"):
    resultado = pipeline.answer(pergunta)
    st.markdown(f"<div class='answer'>{html.escape(resultado.answer)}</div>", unsafe_allow_html=True)
    st.caption(f"Geração: {resultado.generator}. Abstenção: {'sim' if resultado.abstained else 'não'}.")
    if resultado.passages:
        with st.expander("Trechos usados"):
            for doc in resultado.passages:
                st.markdown(f"**{doc.title}**")
                st.write(doc.text)
    if resultado.decisions:
        st.dataframe(
            [
                {
                    "decisão": item.name,
                    "tipo": item.kind,
                    "valor": item.value,
                    "confiança": round(item.confidence, 3),
                    "backend": item.backend,
                    "detalhe": item.detail,
                }
                for item in resultado.decisions
            ],
            use_container_width=True,
            hide_index=True,
        )

footer(
    "Sem LLM_API_KEY a resposta é extrativa: ela reproduz os trechos escolhidos. "
    "Sem JEV_API_URL as decisões usam o classificador local, com saída limitada a probabilidade, escolha ou nota. "
    "O mesmo fluxo está na ferramenta MCP responder."
)
