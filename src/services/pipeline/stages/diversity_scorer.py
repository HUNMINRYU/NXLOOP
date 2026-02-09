from typing import Any

import numpy as np

from services.pipeline.types import Candidate


class MultiFactorDiversityScorer:
    """
    X-Algorithm의 다양성 확보 로직 고도화:
    1. Author/Format/Topic Diversity (Categorical)
    2. Semantic Diversity (Vector-based): 텍스트의 의미적 유사성 기반 도배 방지
    """

    def __init__(
        self,
        author_decay: float = 0.7,
        format_decay: float = 0.5,
        semantic_threshold: float = 0.88, # 이 유사도 이상이면 의미적으로 중복이라 판단
        floor: float = 0.2
    ):
        self.author_decay = author_decay
        self.format_decay = format_decay
        self.semantic_threshold = semantic_threshold
        self.floor = floor

    def _calculate_multiplier(self, count: int, decay: float) -> float:
        if count == 0:
            return 1.0
        return max(self.floor, (decay ** count))

    def _cosine_similarity(self, v1: list[float], v2: list[float]) -> float:
        """두 벡터 간의 코사인 유사도 계산"""
        if not v1 or not v2: return 0.0
        a, b = np.array(v1), np.array(v2)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0: return 0.0
        return np.dot(a, b) / (norm_a * norm_b)

    def apply(self, candidates: list[Candidate], history_context: dict[str, Any] | None = None) -> list[Candidate]:
        author_counts: dict[str, int] = {}
        format_counts: dict[str, int] = {}
        topic_counts: dict[str, int] = {}

        # 의미적 중복 체크를 위한 이전 벡터들 보관 (현재 윈도우 내)
        seen_embeddings: list[list[float]] = []
        if history_context:
            seen_embeddings = history_context.get("recent_embeddings", [])

        for candidate in candidates:
            # 1. Categorical Diversity (Author, Format, Topic)
            author = candidate.author.username if candidate.author else "unknown"
            author_count = author_counts.get(author, 0)
            author_multiplier = self._calculate_multiplier(author_count, self.author_decay)

            content_format = candidate.metadata.get("format", "unknown")
            format_count = format_counts.get(content_format, 0)
            format_multiplier = self._calculate_multiplier(format_count, self.format_decay)

            topic = candidate.category or "general"
            topic_count = topic_counts.get(topic, 0)
            topic_multiplier = self._calculate_multiplier(topic_count, self.author_decay)

            # 2. Semantic Diversity (의미론적 중복 체크)
            semantic_multiplier = 1.0
            current_embedding = candidate.metadata.get("embedding")

            if current_embedding:
                for past_emb in seen_embeddings:
                    sim = self._cosine_similarity(current_embedding, past_emb)
                    if sim > self.semantic_threshold:
                        # 유사도 0.88-1.0 사이를 패널티 구간으로 설정
                        penalty_weight = (sim - self.semantic_threshold) / (1.0 - self.semantic_threshold)
                        semantic_multiplier *= (1.0 - (penalty_weight * 0.4)) # 최대 40%까지 감점

            # 최종 점수 보정
            semantic_multiplier = max(self.floor, semantic_multiplier)
            final_multiplier = author_multiplier * format_multiplier * topic_multiplier * semantic_multiplier
            candidate.score.final_score *= final_multiplier

            # 설명 업데이트
            if final_multiplier < 1.0:
                reasons = []
                if author_multiplier < 1.0: reasons.append(f"Author({author_count})")
                if format_multiplier < 1.0: reasons.append(f"Format({format_count})")
                if semantic_multiplier < 1.0: reasons.append("Semantic(Sim)")

                candidate.score.weighted_components["diversity_multiplier"] = round(final_multiplier, 3)
                candidate.score.explanation += f" [중복 패널티: {', '.join(reasons)}]"

            # 상태 업데이트
            author_counts[author] = author_count + 1
            format_counts[content_format] = format_count + 1
            topic_counts[topic] = topic_count + 1
            if current_embedding:
                seen_embeddings.append(current_embedding)

        return sorted(candidates, key=lambda c: c.score.final_score, reverse=True)

# 하위 호환성을 위한 별칭 설정
AuthorDiversityScorer = MultiFactorDiversityScorer
