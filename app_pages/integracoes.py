from __future__ import annotations

import streamlit as st

from dash_ibge.services.status import probe_stack
from dash_ibge.ui.common import header
from dash_ibge.ui.loaders import carregar_painel

header("Integrações", "O que está ativo nesta máquina e como ligar o que ainda falta.")
status = probe_stack()
painel = carregar_painel()

cards = st.columns(4)
cards[0].metric("Cache", status["redis"]["backend"])
cards[1].metric("Spark", status["spark"]["estado"])
cards[2].metric("Jev", status["jev"]["backend"])
cards[3].metric("LLM", "ativo" if status["llm"]["configurado"] else "extrativo")
st.caption(status["redis"]["detalhe"])
st.caption(f"Leitura do Censo guardada em: {painel.cache_backend}. {painel.cache_detail}")

st.subheader("Redis gratuito")
st.markdown(
    """
O `docker-compose.yml` sobe o Redis 7.2, a linha com licença BSD, sem módulos pagos.
Com o servidor no ar, as respostas da API ficam 12 horas em `REDIS_URL`.
Se ele não responder, o processo usa memória e o painel continua.
"""
)
st.code("docker compose up -d", language="powershell")

st.subheader("PySpark")
st.markdown(
    f"""
Modo atual: `{status['spark']['modo']}`. Pacote instalado: `{status['spark']['pacote']}`. Java no PATH: `{status['spark']['java']}`.
No modo `auto`, a soma dos municípios passa pelo Spark local só quando o pacote e o Java existem.
Caso contrário a mesma agregação roda no Polars.
"""
)
st.code('pip install -e ".[spark]"', language="powershell")

st.subheader("LLM, RAG, Jev e MCP")
st.markdown(
    """
O assistente recupera trechos dos indicadores (RAG). Antes de responder, um modelo de decisão
aceita ou recusa cada trecho, julga se a evidência basta e se a resposta permanece nos números.
Esse contrato é o de um Jev: probabilidade, escolha ou nota, nunca texto livre.

`JEV_API_URL` troca o classificador local por um endpoint que devolve `noul` entre 0 e 1.
`LLM_API_KEY` liga um chat compatível com a API da OpenAI. Sem a chave, a resposta copia os trechos.

O servidor MCP expõe as mesmas consultas para um cliente como o Cursor:

`status_integracoes`, `listar_ufs`, `indicadores_uf`, `ranking` e `responder`.
"""
)
st.code(
    """{
  "mcpServers": {
    "ibge-censo": {
      "command": "python",
      "args": ["-m", "dash_ibge.mcp_server"]
    }
  }
}""",
    language="json",
)
st.caption("Rode o comando a partir da raiz do projeto, com o pacote instalado no mesmo Python.")
