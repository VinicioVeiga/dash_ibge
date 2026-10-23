from __future__ import annotations

import numpy as np


def finite_column(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    return array[np.isfinite(array)]


def zscores(matrix: np.ndarray) -> np.ndarray:
    means = np.nanmean(matrix, axis=0)
    stds = np.nanstd(matrix, axis=0)
    stds = np.where(stds < 1e-12, 1.0, stds)
    return (matrix - means) / stds


def correlation(matrix: np.ndarray) -> np.ndarray:
    if matrix.shape[0] < 3 or matrix.shape[1] < 2:
        return np.full((matrix.shape[1], matrix.shape[1]), np.nan)
    centered = matrix - np.mean(matrix, axis=0)
    stds = np.std(centered, axis=0)
    usable = stds > 1e-12
    result = np.full((matrix.shape[1], matrix.shape[1]), np.nan)
    if usable.sum() < 2:
        return result
    reduced = centered[:, usable] / stds[usable]
    corr = (reduced.T @ reduced) / max(matrix.shape[0] - 1, 1)
    idx = np.flatnonzero(usable)
    result[np.ix_(idx, idx)] = corr
    return result


def index_against(values: np.ndarray, reference: float) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if not np.isfinite(reference) or reference == 0:
        return np.full(array.shape, np.nan)
    return array / reference * 100


def log_histogram(values: np.ndarray, bins: int = 18) -> tuple[np.ndarray, np.ndarray]:
    array = finite_column(values)
    array = array[array > 0]
    if array.size == 0:
        return np.array([]), np.array([])
    logs = np.log10(array)
    counts, edges = np.histogram(logs, bins=min(bins, max(array.size, 1)))
    return counts.astype(float), np.power(10, edges)


def share(part: float | None, whole: float | None) -> float | None:
    if part is None or whole is None or whole == 0:
        return None
    if not np.isfinite(part) or not np.isfinite(whole):
        return None
    return float(part) / float(whole) * 100
