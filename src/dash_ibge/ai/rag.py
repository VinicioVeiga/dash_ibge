from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from dash_ibge.ai.corpus import Document, fold
from dash_ibge.ai.jev import Decision, HttpJevBackend, LocalJevBackend, build_jev
from dash_ibge.ai.llm import LlmClient
from dash_ibge.cache.store import MemoryCache, ResponseCache
from dash_ibge.config import Settings, get_settings

_NUMBER = re.compile(r"\d{4,}")


@dataclass
class RagAnswer:
    answer: str
    abstained: bool
    passages: list[Document] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    generator: str = "extrativo"


class CensusIndex:
    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents
        folded = [fold(doc.title + " " + doc.text) for doc in documents]
        if not folded:
            self._matrix = np.zeros((0, 1))
            self._vectorizer = None
            return
        self._vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
        matrix = self._vectorizer.fit_transform(folded).toarray().astype(float)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms = np.where(norms < 1e-12, 1.0, norms)
        self._matrix = matrix / norms

    def search(self, question: str, limit: int = 8) -> list[tuple[Document, float]]:
        if self._vectorizer is None or not self.documents:
            return []
        query = self._vectorizer.transform([fold(question)]).toarray().astype(float)
        norm = np.linalg.norm(query)
        if norm < 1e-12:
            return []
        query = query / norm
        scores = (self._matrix @ query.T).ravel()
        order = np.argsort(scores)[::-1][:limit]
        return [(self.documents[int(index)], float(scores[int(index)])) for index in order if scores[int(index)] > 0]


class RagPipeline:
    def __init__(
        self,
        documents: list[Document],
        settings: Settings | None = None,
        cache: ResponseCache | None = None,
        jev: LocalJevBackend | None = None,
        llm: LlmClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.index = CensusIndex(documents)
        self.cache = cache or MemoryCache("Cache de respostas neste processo.")
        self.jev = jev or build_jev(self.settings)
        self.local = self.jev if isinstance(self.jev, LocalJevBackend) else self.jev.fallback
        self.llm = llm or LlmClient(self.settings)

    def answer(self, question: str) -> RagAnswer:
        question = question.strip()
        decisions: list[Decision] = []
        if len(question) < 3:
            decisions.append(self.local.decide("suficiencia", "noul", 0.0, 0.0, detail="Pergunta curta demais."))
            return RagAnswer("Escreva uma pergunta sobre o Censo.", True, decisions=decisions)

        cache_key = f"rag:{fold(question)}"
        cached = self.cache.get(cache_key)
        if isinstance(cached, dict) and cached.get("answer"):
            similarity = _overlap(question, str(cached.get("question", "")))
            trust = self.local.decide(
                "confianca-cache",
                "noul",
                similarity,
                similarity,
                1.0,
                detail="Comparação entre a pergunta atual e a pergunta armazenada.",
            )
            decisions.append(trust)
            if similarity >= 0.97 and float(trust.value) >= self.local.high * 0.9:
                return RagAnswer(
                    str(cached["answer"]),
                    bool(cached.get("abstained")),
                    passages=[],
                    decisions=decisions,
                    generator=str(cached.get("generator", "cache")),
                )

        ranked = self.index.search(question)
        judged: list[tuple[Document, float, float, Decision]] = []
        for doc, score in ranked:
            overlap = _overlap(question, doc.text)
            decision = self.local.decide(
                "selecao-contexto",
                "choice",
                score,
                overlap,
                min(1.0, score * 2),
                detail=doc.title,
            )
            judged.append((doc, score, overlap, decision))
        best_score = judged[0][1] if judged else 0.0
        selected = [
            item
            for item in judged
            if item[3].value == "aceitar" and item[1] >= best_score * 0.62
        ][:4]
        for document, score, token_overlap, decision in selected:
            decisions.append(decision)
        if not selected and judged:
            decisions.append(judged[0][3])

        best_overlap = judged[0][2] if judged else 0.0
        evidence_preview = "\n".join(doc.text for doc, _score, _overlap, _decision in selected) or (
            judged[0][0].text if judged else ""
        )
        if isinstance(self.jev, HttpJevBackend) and selected:
            sufficiency = self.jev.decide_remote(
                "suficiencia",
                f"Os trechos bastam para responder: {question}",
                evidence_preview,
            )
        else:
            sufficiency = self.local.decide(
                "suficiencia",
                "noul",
                best_score,
                best_overlap,
                min(1.0, best_score * 2),
                detail="O melhor trecho precisa sustentar a resposta.",
            )
        decisions.append(sufficiency)
        chosen = [(doc, score) for doc, score, _overlap, _decision in selected]
        if not chosen or float(sufficiency.value) < self.local.threshold:
            answer = (
                "Não há evidência suficiente nos indicadores carregados para responder com segurança. "
                "Tente perguntar por uma UF, uma região, população, alfabetização, idade, cor ou raça, "
                "urbanização ou a série histórica."
            )
            result = RagAnswer(answer, True, [doc for doc, _score in chosen], decisions, "abstencao")
            self._store(cache_key, question, result)
            return result

        evidence = "\n\n".join(f"[{doc.title}] {doc.text}" for doc, _score in chosen)
        generator = "extrativo"
        if self.llm.configured:
            try:
                draft = self.llm.answer(question, evidence)
                generator = f"llm:{self.settings.llm_model}"
            except Exception as exc:
                draft = _extractive(question, chosen)
                generator = "extrativo"
                decisions.append(
                    Decision(
                        "geracao",
                        "score",
                        "0.000",
                        0.0,
                        "extrativo",
                        f"O LLM falhou ({exc.__class__.__name__}). A resposta ficou extrativa.",
                    )
                )
        else:
            draft = _extractive(question, chosen)

        grounded = _numbers_grounded(draft, evidence)
        overlap = _overlap(draft, evidence)
        if isinstance(self.jev, HttpJevBackend):
            abstain = self.jev.decide_remote(
                "abstencao",
                "A resposta usa somente números presentes nos trechos?",
                f"Resposta:\n{draft}\n\nTrechos:\n{evidence}",
            )
        else:
            abstain = self.local.decide(
                "abstencao",
                "noul",
                overlap,
                1.0 if grounded else 0.0,
                1.0,
                detail="A resposta precisa permanecer nos números dos trechos.",
            )
        decisions.append(abstain)
        if not grounded or float(abstain.value) < self.local.threshold * 0.75:
            draft = (
                "A resposta gerada não ficou ancorada nos trechos recuperados, então ela foi retida. "
                + _extractive(question, chosen)
            )
            generator = "extrativo-apos-abstencao"
            abstained = False
        else:
            abstained = False
        result = RagAnswer(draft, abstained, [item[0] for item in selected], decisions, generator)
        self._store(cache_key, question, result)
        return result

    def _store(self, key: str, question: str, result: RagAnswer) -> None:
        self.cache.set(
            key,
            {
                "question": question,
                "answer": result.answer,
                "abstained": result.abstained,
                "generator": result.generator,
            },
            self.settings.cache_ttl_seconds,
        )


def _extractive(question: str, selected: list[tuple[Document, float]]) -> str:
    lines = ["Com base nos indicadores do Censo consultados na API do IBGE:"]
    for doc, score in selected:
        lines.append(f"- {doc.title}: {doc.text}")
    lines.append(f"Pergunta considerada: {question}")
    return "\n".join(lines)


def _overlap(left: str, right: str) -> float:
    tokens_left = {token for token in fold(left).split() if len(token) > 2}
    tokens_right = {token for token in fold(right).split() if len(token) > 2}
    if not tokens_left or not tokens_right:
        return 0.0
    return len(tokens_left & tokens_right) / len(tokens_left)


def _numbers_grounded(answer: str, evidence: str) -> bool:
    answer_numbers = set(_NUMBER.findall(answer.replace(".", "").replace(",", "")))
    evidence_numbers = set(_NUMBER.findall(evidence.replace(".", "").replace(",", "")))
    return answer_numbers.issubset(evidence_numbers)
