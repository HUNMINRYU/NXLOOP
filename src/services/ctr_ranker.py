from __future__ import annotations

from pathlib import Path
from typing import Any

from services.ctr_predictor import CTRPredictor
from services.ctr_ranker_artifact import CTRRankerArtifact


class CTRRanker:
    """
    before/after 비교를 위해 baseline(기존 CTRPredictor total_score)과
    after(학습된 선형 모델 score)을 함께 제공한다.
    """

    def __init__(
        self,
        *,
        predictor: CTRPredictor,
        artifact: CTRRankerArtifact,
    ) -> None:
        self._predictor = predictor
        self._artifact = artifact

    @classmethod
    def from_artifact_path(
        cls,
        *,
        predictor: CTRPredictor,
        artifact_path: str | Path,
    ) -> CTRRanker:
        artifact = CTRRankerArtifact.load_json(artifact_path)
        return cls(predictor=predictor, artifact=artifact)

    def score(
        self,
        *,
        title: str,
        thumbnail_description: str = "",
        competitor_titles: list[str] | None = None,
    ) -> dict[str, Any]:
        features = self._predictor.extract_features(
            title=title,
            thumbnail_description=thumbnail_description,
            competitor_titles=competitor_titles or [],
        )

        breakdown = dict(features["breakdown"])
        baseline_score = float(features["total_score"])
        ml_score = float(self._artifact.score_from_features(breakdown))

        return {
            "baseline_score": baseline_score,
            "ml_score": ml_score,
            "features": breakdown,
        }

