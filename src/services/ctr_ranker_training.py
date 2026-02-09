from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import numpy as np

from services.ctr_ranker_artifact import CTRRankerArtifact


@dataclass(frozen=True)
class TrainingResult:
    artifact: CTRRankerArtifact
    metrics: dict[str, float]


def _standardize(x: np.ndarray) -> tuple[np.ndarray, list[float], list[float]]:
    if x.ndim != 2:
        raise ValueError("X는 2차원 행렬이어야 합니다.")
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    std_safe = np.where(std == 0.0, 1.0, std)
    xz = (x - mean) / std_safe
    return xz, mean.astype(float).tolist(), std_safe.astype(float).tolist()


def train_linear_ridge_ranker(
    *,
    feature_names: list[str],
    x: np.ndarray,
    y: np.ndarray,
    alpha: float = 1.0,
    training_meta: dict[str, Any] | None = None,
) -> CTRRankerArtifact:
    """
    sklearn 없이도 재현 가능한 Ridge 회귀 학습(폐형 해).

    - X: shape (n_samples, n_features)
    - y: shape (n_samples,)
    - alpha: L2 규제 강도
    """
    if x.ndim != 2:
        raise ValueError("X는 2차원이어야 합니다.")
    if y.ndim != 1:
        raise ValueError("y는 1차원이어야 합니다.")
    if x.shape[0] != y.shape[0]:
        raise ValueError("X와 y의 샘플 수가 일치하지 않습니다.")
    if x.shape[1] != len(feature_names):
        raise ValueError("feature_names 길이와 X feature 수가 일치하지 않습니다.")

    xz, mean, std = _standardize(x)
    n, d = xz.shape

    # intercept 포함: [Xz | 1]
    ones = np.ones((n, 1), dtype=float)
    xa = np.hstack([xz, ones])

    # Ridge: (Xa^T Xa + alpha*I)^{-1} Xa^T y, 단 intercept는 규제 제외
    eye = np.eye(d + 1, dtype=float)
    eye[-1, -1] = 0.0

    a_mat = xa.T @ xa + alpha * eye
    b_vec = xa.T @ y.astype(float)
    w_all = np.linalg.solve(a_mat, b_vec)

    weights = w_all[:d].astype(float).tolist()
    intercept = float(w_all[-1])

    meta = dict(training_meta or {})
    meta.update(
        {
            "alpha": float(alpha),
            "n_samples": int(n),
            "n_features": int(d),
        }
    )

    created_at_iso = datetime.now(timezone.utc).isoformat()
    return CTRRankerArtifact(
        version="v1",
        created_at_iso=created_at_iso,
        feature_names=list(feature_names),
        scaler_mean=mean,
        scaler_std=std,
        weights=weights,
        intercept=intercept,
        training_meta=meta,
    )
