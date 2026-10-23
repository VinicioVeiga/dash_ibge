from __future__ import annotations

import httpx

from dash_ibge.config import Settings


class LlmClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def configured(self) -> bool:
        return self.settings.llm_configured

    def answer(self, question: str, evidence: str) -> str:
        if not self.configured:
            raise RuntimeError("LLM_API_KEY não configurada.")
        payload = {
            "model": self.settings.llm_model,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Você responde em português sobre o Censo Demográfico do Brasil. "
                        "Use somente os trechos fornecidos. Não invente números. "
                        "Se os trechos não sustentarem a resposta, diga que a evidência é insuficiente. "
                        "Cite a UF ou o recorte e o ano quando houver."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Pergunta:\n{question}\n\nTrechos:\n{evidence}",
                },
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        response = httpx.post(
            f"{self.settings.llm_base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=45,
        )
        response.raise_for_status()
        body = response.json()
        return str(body["choices"][0]["message"]["content"]).strip()
