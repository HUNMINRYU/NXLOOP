"""Similarity Reranker - Candidate feature와 User Profile 간 코사인 유사도 리랭킹"""

from __future__ import annotations

import math

from services.pipeline.stages.user_profile import UserProfile
from services.pipeline.types import Candidate

# CandidateFeatures에서 벡터로 변환할 필드 목록 (19-dim)
FEATURE_KEYS = [
    "purchase_intent",
    "constructive_feedback",
    "reply_inducing",
    "share_probability",
    "viral_potential",
    "actionable_insight",
    "quote_worthy",
    "save_worthy",
    "follow_author",
    "sentiment_intensity",
    "dwell_time",
    "toxicity",
    "controversy_score",
    "not_interested",
    "report_probability",
    "dm_probability",
    "copy_link_probability",
    "profile_click",
    "bookmark_worthy",
]


def _candidate_to_vector(candidate: Candidate) -> list[float]:
    """CandidateFeatures를 19차원 벡터로 변환"""
    features = candidate.features
    return [getattr(features, key, 0.0) for key in FEATURE_KEYS]


def _profile_to_vector(profile: UserProfile) -> list[float]:
    """UserProfile의 preferred_features를 19차원 벡터로 변환"""
    return [profile.preferred_features.get(key, 0.0) for key in FEATURE_KEYS]


def _dot_product(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=False))


def _magnitude(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    mag_a = _magnitude(a)
    mag_b = _magnitude(b)
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return _dot_product(a, b) / (mag_a * mag_b)


class SimilarityReranker:
    """
    Candidate의 feature vector와 User Profile의 선호도 간 코사인 유사도로 리랭킹.
    final = alpha * original_score + (1 - alpha) * similarity_score
    """

    def __init__(self, profile: UserProfile | None = None, alpha: float = 0.7):
        self.profile = profile
        self.alpha = alpha

    async def rerank(self, candidates: list[Candidate]) -> list[Candidate]:
        """프로필 기반 리랭킹 (프로필 없으면 원본 반환)"""
        if self.profile is None or not self.profile.preferred_features:
            return candidates

        profile_vec = _profile_to_vector(self.profile)
        if _magnitude(profile_vec) == 0:
            return candidates

        # 기존 점수 범위 확인 (정규화용)
        scores = [c.score.final_score for c in candidates]
        max_score = max(scores) if scores else 1.0
        min_score = min(scores) if scores else 0.0
        score_range = max_score - min_score if max_score != min_score else 1.0

        for candidate in candidates:
            cand_vec = _candidate_to_vector(candidate)
            similarity = _cosine_similarity(cand_vec, profile_vec)

            # 기존 점수를 0~1로 정규화
            normalized_original = (
                (candidate.score.final_score - min_score) / score_range
            )

            # Blending
            blended = self.alpha * normalized_original + (1 - self.alpha) * similarity

            # 원래 스케일로 복원
            candidate.score.final_score = round(
                blended * score_range + min_score, 2
            )
            candidate.score.weighted_components["similarity"] = round(similarity, 3)

        return sorted(candidates, key=lambda c: c.score.final_score, reverse=True)
