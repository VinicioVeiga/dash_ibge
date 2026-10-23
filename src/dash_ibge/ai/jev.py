from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression


@dataclass(frozen=True)
class Decision:
    name: str
    kind: str
    value: str
    confidence: float
    backend: str
    detail: str


class LocalJevBackend:
    """Decisões limitadas a probabilidade, nota ou escolha.

    O modelo local é um classificador calibrado em exemplos sintéticos. Ele ocupa
    o mesmo contrato de um Jev remoto: recebe evidência numérica e devolve uma
    probabilidade entre 0 e 1, sem gerar texto.
    """

    name = "jev-local"

    def __init__(self) -> None:
        rng = np.random.default_rng(7)
        similarity = rng.uniform(0.0, 0.75, 480)
        overlap = rng.uniform(0.0, 1.0, 480)
        coverage = rng.uniform(0.0, 1.0, 480)
        features = np.column_stack([similarity, overlap, coverage])
        signal = 0.45 * similarity + 0.50 * overlap + 0.05 * coverage
        labels = (signal >= 0.22).astype(int)
        labels[0] = 0
        labels[1] = 1
        self.model = LogisticRegression(random_state=7)
        self.model.fit(features, labels)
        low = self._proba(np.array([[0.02, 0.0, 0.0]]))
        high = self._proba(np.array([[0.85, 0.70, 0.80]]))
        self.threshold = float((low + high) / 2)
        self.high = float(high)

    def noul(self, similarity: float, overlap: float, coverage: float = 0.0) -> tuple[float, float]:
        probability = self._proba(np.array([[similarity, overlap, coverage]], dtype=float))
        confidence = float(np.clip(abs(probability - 0.5) * 2, 0, 1))
        return probability, confidence

    def decide(
        self,
        name: str,
        kind: str,
        similarity: float,
        overlap: float,
        coverage: float = 0.0,
        detail: str = "",
    ) -> Decision:
        probability, confidence = self.noul(similarity, overlap, coverage)
        if kind == "choice":
            value = "aceitar" if probability >= self.threshold else "recusar"
        else:
            value = f"{probability:.3f}"
        return Decision(name, kind, value, confidence, self.name, detail)

    def _proba(self, features: np.ndarray) -> float:
        clipped = np.clip(features, 0.0, 1.0)
        return float(self.model.predict_proba(clipped)[0, 1])


class HttpJevBackend:
    """Adaptador para um endpoint Jev que devolve noul entre 0 e 1."""

    name = "jev-http"

    def __init__(self, url: str, api_key: str, model: str, fallback: LocalJevBackend) -> None:
        self.url = url
        self.api_key = api_key
        self.model = model
        self.fallback = fallback
        self.threshold = fallback.threshold
        self.high = fallback.high

    def noul(self, similarity: float, overlap: float, coverage: float = 0.0) -> tuple[float, float]:
        return self.fallback.noul(similarity, overlap, coverage)

    def decide_remote(self, name: str, proposition: str, evidence: str) -> Decision:
        import httpx

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "input": {"task": "noul", "proposition": proposition, "evidence": evidence[:6000]},
        }
        try:
            response = httpx.post(self.url, json=payload, headers=headers, timeout=20)
            response.raise_for_status()
            body = response.json()
            probability = _extract_noul(body)
        except Exception as exc:
            local = self.fallback.decide(name, "noul", 0.0, 0.0, detail="")
            return Decision(
                name,
                "noul",
                local.value,
                local.confidence,
                self.fallback.name,
                f"Endpoint Jev indisponível ({exc.__class__.__name__}). Decisão local usada no lugar.",
            )
        if probability is None:
            local = self.fallback.decide(name, "noul", 0.0, 0.0)
            return Decision(
                name,
                "noul",
                local.value,
                local.confidence,
                self.fallback.name,
                "A resposta do endpoint não trouxe noul. Decisão local usada no lugar.",
            )
        probability = float(np.clip(probability, 0.0, 1.0))
        confidence = float(np.clip(abs(probability - 0.5) * 2, 0, 1))
        return Decision(name, "noul", f"{probability:.3f}", confidence, self.name, "Decisão remota.")


def build_jev(settings) -> LocalJevBackend | HttpJevBackend:
    local = LocalJevBackend()
    if settings.jev_remote:
        return HttpJevBackend(settings.jev_api_url, settings.jev_api_key, settings.jev_model, local)
    return local


def _extract_noul(body: object) -> float | None:
    if isinstance(body, (int, float)):
        return float(body)
    if not isinstance(body, dict):
        return None
    for key in ("noul", "probability", "yes", "score"):
        value = body.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    for key in ("result", "output", "data"):
        if key in body:
            found = _extract_noul(body[key])
            if found is not None:
                return found
    return None
