from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CTRRankerArtifact:
    """
    경량 CTR 랭킹 모델 아티팩트.

    - 학습은 scikit-learn 등으로 수행할 수 있지만,
      런타임(서비스) 추론은 numpy 없이도 가능한 선형 스코어링만 제공한다.
    - 피처 표준화: (x - mean) / std
    - 스코어: w·x + b
    """

    version: str
    created_at_iso: str
    feature_names: list[str]
    scaler_mean: list[float]
    scaler_std: list[float]
    weights: list[float]
    intercept: float
    training_meta: dict[str, Any]

    def score_from_features(self, features: dict[str, float]) -> float:
        if len(self.feature_names) != len(self.weights):
            raise ValueError("feature_names/weights 길이가 일치하지 않습니다.")
        if len(self.feature_names) != len(self.scaler_mean) or len(self.feature_names) != len(
            self.scaler_std
        ):
            raise ValueError("feature_names/scaler 파라미터 길이가 일치하지 않습니다.")

        s = float(self.intercept)
        for i, name in enumerate(self.feature_names):
            raw = float(features.get(name, 0.0))
            mean = float(self.scaler_mean[i])
            std = float(self.scaler_std[i])
            z = 0.0 if std == 0.0 else (raw - mean) / std
            s += float(self.weights[i]) * z
        return float(s)

    @classmethod
    def load_json(cls, path: str | Path) -> CTRRankerArtifact:
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls(
            version=str(data.get("version", "v1")),
            created_at_iso=str(data.get("created_at_iso", datetime.now().isoformat())),
            feature_names=list(data["feature_names"]),
            scaler_mean=[float(x) for x in data["scaler_mean"]],
            scaler_std=[float(x) for x in data["scaler_std"]],
            weights=[float(x) for x in data["weights"]],
            intercept=float(data.get("intercept", 0.0)),
            training_meta=dict(data.get("training_meta", {})),
        )

    def dump_json(self, path: str | Path) -> None:
        p = Path(path)
        payload = {
            "version": self.version,
            "created_at_iso": self.created_at_iso,
            "feature_names": self.feature_names,
            "scaler_mean": self.scaler_mean,
            "scaler_std": self.scaler_std,
            "weights": self.weights,
            "intercept": self.intercept,
            "training_meta": self.training_meta,
        }
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
