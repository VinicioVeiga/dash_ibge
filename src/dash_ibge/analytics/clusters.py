from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import polars as pl
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

FEATURE_LABELS: dict[str, str] = {
    "densidade": "Densidade (hab/km²)",
    "taxa_alfabetizacao": "Alfabetização 15+ (%)",
    "indice_envelhecimento": "Índice de envelhecimento",
    "idade_mediana": "Idade mediana (anos)",
    "razao_sexo": "Razão de sexo",
    "pct_urbana": "População urbana (%)",
    "taxa_crescimento": "Crescimento geométrico (%)",
    "pct_branca": "Branca (%)",
    "pct_parda": "Parda (%)",
    "moradores_por_domicilio": "Pessoas por domicílio ocupado",
}

_HIGH_LOW = {
    "densidade": ("densidade demográfica mais alta", "densidade demográfica mais baixa"),
    "taxa_alfabetizacao": ("alfabetização mais alta", "alfabetização mais baixa"),
    "indice_envelhecimento": ("envelhecimento mais acentuado", "envelhecimento menos acentuado"),
    "idade_mediana": ("idade mediana mais alta", "idade mediana mais baixa"),
    "razao_sexo": ("maior razão de sexo", "menor razão de sexo"),
    "pct_urbana": ("maior grau de urbanização", "menor grau de urbanização"),
    "taxa_crescimento": ("crescimento mais rápido", "crescimento mais lento"),
    "pct_branca": ("maior percentual de pessoas brancas", "menor percentual de pessoas brancas"),
    "pct_parda": ("maior percentual de pessoas pardas", "menor percentual de pessoas pardas"),
    "moradores_por_domicilio": ("domicílios mais populosos", "domicílios menos populosos"),
}


@dataclass
class ClusterResult:
    frame: pl.DataFrame
    features: list[str]
    labels_features: list[str]
    k: int
    silhouette: float
    silhouettes: dict[int, float]
    centers: np.ndarray
    explained: np.ndarray
    correlation: np.ndarray
    summaries: list[str] = field(default_factory=list)
    imputed: list[str] = field(default_factory=list)


def cluster_ufs(frame: pl.DataFrame, k: int | None = None, k_max: int = 5) -> ClusterResult:
    available = [name for name in FEATURE_LABELS if name in frame.columns]
    work = frame.select(
        [column for column in ("sigla", "nome", "regiao", "localidade_id") if column in frame.columns] + available
    ).drop_nulls(subset=["sigla"])
    matrix, used, imputed = _matrix(work, available)
    if matrix.shape[0] < 4 or matrix.shape[1] < 2:
        raise ValueError("Indicadores insuficientes para agrupar as UFs.")

    scaler = StandardScaler()
    scaled = scaler.fit_transform(matrix)
    chosen, scores = _choose_k(scaled, k, k_max)
    model = KMeans(n_clusters=chosen, n_init=20, random_state=7)
    labels = model.fit_predict(scaled)
    score = float(silhouette_score(scaled, labels))
    coords, explained = _pca(scaled)
    centers = scaler.inverse_transform(model.cluster_centers_)
    means = matrix.mean(axis=0)
    stds = np.where(matrix.std(axis=0) < 1e-12, 1.0, matrix.std(axis=0))
    center_z = (centers - means) / stds
    summaries = [_summary(row, used) for row in center_z]

    corr = _corr(scaled)
    labeled = work.with_columns(
        pl.Series("grupo", (labels + 1).tolist()),
        pl.Series("pca_1", coords[:, 0].tolist()),
        pl.Series("pca_2", coords[:, 1].tolist()),
    ).sort(["grupo", "sigla"])
    return ClusterResult(
        frame=labeled,
        features=used,
        labels_features=[FEATURE_LABELS[name] for name in used],
        k=chosen,
        silhouette=score,
        silhouettes=scores,
        centers=centers,
        explained=explained,
        correlation=corr,
        summaries=summaries,
        imputed=imputed,
    )


def _matrix(frame: pl.DataFrame, columns: list[str]) -> tuple[np.ndarray, list[str], list[str]]:
    used: list[str] = []
    imputed: list[str] = []
    columns_data: list[np.ndarray] = []
    for name in columns:
        values = frame.get_column(name).to_numpy().astype(float)
        finite = np.isfinite(values)
        if finite.sum() < max(4, int(0.6 * len(values))):
            continue
        filled = values.copy()
        if (~finite).any():
            filled[~finite] = float(np.nanmedian(values))
            imputed.append(FEATURE_LABELS[name])
        if np.nanstd(filled) < 1e-9:
            continue
        columns_data.append(filled)
        used.append(name)
    if not columns_data:
        return np.empty((frame.height, 0)), [], imputed
    return np.column_stack(columns_data), used, imputed


def _choose_k(scaled: np.ndarray, k: int | None, k_max: int) -> tuple[int, dict[int, float]]:
    limit = min(k_max, scaled.shape[0] - 1)
    scores: dict[int, float] = {}
    if k is not None:
        chosen = min(max(int(k), 2), limit)
        labels = KMeans(n_clusters=chosen, n_init=10, random_state=7).fit_predict(scaled)
        scores[chosen] = float(silhouette_score(scaled, labels))
        return chosen, scores
    best_k, best_score = 2, -1.0
    for candidate in range(2, limit + 1):
        labels = KMeans(n_clusters=candidate, n_init=10, random_state=7).fit_predict(scaled)
        score = float(silhouette_score(scaled, labels))
        scores[candidate] = score
        if score > best_score:
            best_k, best_score = candidate, score
    return best_k, scores


def _pca(scaled: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    centered = scaled - scaled.mean(axis=0)
    _, singular, vectors = np.linalg.svd(centered, full_matrices=False)
    coords = centered @ vectors[:2].T
    variance = singular**2
    explained = variance / variance.sum() if variance.sum() else variance
    return coords, explained[:2]


def _corr(scaled: np.ndarray) -> np.ndarray:
    if scaled.shape[0] < 3:
        return np.eye(scaled.shape[1])
    return np.corrcoef(scaled, rowvar=False)


def _summary(center_z: np.ndarray, features: list[str]) -> str:
    order = np.argsort(center_z)
    high = [features[index] for index in order[::-1] if center_z[index] >= 0.55][:2]
    low = [features[index] for index in order if center_z[index] <= -0.55][:2]
    parts: list[str] = []
    parts.extend(_HIGH_LOW[name][0] for name in high)
    parts.extend(_HIGH_LOW[name][1] for name in low)
    if not parts:
        return "Perfil próximo da média das UFs neste conjunto de indicadores."
    text = ", ".join(parts)
    return text[0].upper() + text[1:] + "."
