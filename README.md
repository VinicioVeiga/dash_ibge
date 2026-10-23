# Censo IBGE

Dashboard para ler o Censo Demográfico do Brasil pela API de agregados do IBGE. A tela é Streamlit. O tratamento dos dados fica em Polars, os cálculos em NumPy e o agrupamento das UFs em scikit-learn. Redis, PySpark, LLM e Jev entram quando estão disponíveis e não travam a aplicação quando não estão.

## O que o painel mostra

- População, área, densidade e crescimento geométrico em 2022
- Alfabetização, idade mediana, razão de sexo e índice de envelhecimento
- Pirâmide etária por sexo
- Cor ou raça em 2010 e 2022
- População urbana e rural
- Série nacional desde o censo de 1872
- Municípios da tabela 4714, com agregação por UF
- Grupos de UFs parecidas e a correlação entre indicadores
- Assistente que responde só com os números carregados

## Executar

```powershell
cd C:\Users\vinic\Downloads\dash_ibge
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
streamlit run app.py
```

Abra o endereço que o Streamlit mostrar, em geral `http://localhost:8501`.

## Redis

O arquivo `docker-compose.yml` sobe o Redis 7.2 com licença BSD-3-Clause, a versão gratuita, sem módulos pagos. O aplicativo usa só `PING`, `GET` e `SETEX`.

```powershell
docker compose up -d
```

Se o Redis não responder, o cache daquela execução fica na memória do processo.

## PySpark

```powershell
pip install -e ".[spark]"
```

Também é preciso ter Java no `PATH`. Com `SPARK_ENABLED=auto`, a soma dos municípios usa o Spark local quando os dois existem. O mesmo cálculo roda no Polars nos outros casos. `SPARK_ENABLED=0` força o Polars. `SPARK_ENABLED=1` tenta o Spark e registra o motivo se ele não subir.

## LLM, RAG, Jev e MCP

O assistente monta um texto por UF, região e Brasil, mais um glossário curto, e recupera os trechos por similaridade (RAG). Um classificador local toma quatro decisões de saída fechada, no formato de um Jev:

| Decisão | Saída |
| --- | --- |
| Confiança no cache | probabilidade de reaproveitar a resposta |
| Seleção de contexto | aceitar ou recusar o trecho |
| Suficiência | probabilidade de a evidência bastar |
| Abstenção | probabilidade de a resposta ter ficado nos números |

`JEV_API_URL` aponta para um endpoint que recebe `proposition` e `evidence` e devolve `noul` entre 0 e 1. Sem essa URL, as decisões ficam no classificador local.

`LLM_API_KEY` liga um chat compatível com a API da OpenAI. Sem a chave, a resposta reproduz os trechos escolhidos.

O servidor MCP expõe `status_integracoes`, `listar_ufs`, `indicadores_uf`, `ranking` e `responder`:

```powershell
python -m dash_ibge.mcp_server
```

No Cursor, o servidor pode ficar assim, com o diretório de trabalho na raiz do projeto e o Python do ambiente virtual:

```json
{
  "mcpServers": {
    "ibge-censo": {
      "command": "C:\\Users\\vinic\\Downloads\\dash_ibge\\.venv\\Scripts\\python.exe",
      "args": ["-m", "dash_ibge.mcp_server"]
    }
  }
}
```

## Tabelas do IBGE

| Tabela | Uso |
| --- | --- |
| 4714 | População, área e densidade, inclusive municípios |
| 4709 | Variação desde 2010 e crescimento geométrico |
| 9515 | Envelhecimento, idade mediana e razão de sexo |
| 9543 | Taxa de alfabetização |
| 9605 | Cor ou raça em 2010 e 2022 |
| 9923 | Situação urbana e rural |
| 9514 | Sexo e grupos de idade |
| 4711 | Domicílios particulares permanentes ocupados |
| 1209 | População do Brasil nos censos desde 1872 |

Os números vêm da API. O painel não recalcula o índice de envelhecimento nem a razão de sexo.

## Testes

```powershell
pytest
```

## Variáveis

O arquivo `.env.example` lista `IBGE_BASE_URL`, `REDIS_URL`, `SPARK_ENABLED`, `LLM_API_KEY` e `JEV_API_URL`.
