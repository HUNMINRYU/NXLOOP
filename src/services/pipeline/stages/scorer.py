import asyncio
import math
from typing import Any, ClassVar

from api import validate_json_output
from core.interfaces.ai_service import IMarketingAIService
from core.prompts import prompt_registry
from services.pipeline.types import Candidate, CandidateScore
from utils.logger import get_logger

logger = get_logger(__name__)


class SemanticScorer:
    """
    X-Algorithm 스타일의 간소화된 참여(engagement) 스코어러.

    Gemini를 통해 아래 3개 확률을 예측하고, 가중치 합으로 final_score를 산출합니다.
    - p_dwell: 사용자가 3초 이상 머물 확률 (0.0 ~ 1.0)
    - p_share: 공유할 확률 (0.0 ~ 1.0)
    - p_action: 댓글/클릭 등 행동할 확률 (0.0 ~ 1.0)

    Score = (p_dwell * 0.5) + (p_share * 0.3) + (p_action * 0.2)
    score < 0.7 이면 Candidate.is_slop=True 로 마킹합니다.
    """

    SLOP_THRESHOLD: ClassVar[float] = 0.7

    def __init__(self, gemini_client: IMarketingAIService | None = None) -> None:
        self.gemini_client = gemini_client

    async def score(
        self, candidates: list[Candidate], context: dict[str, Any] | None = None
    ) -> list[Candidate]:
        if not candidates:
            return []

        # AI 클라이언트가 없으면(테스트/로컬) 보수적으로 slop 처리
        if self.gemini_client is None:
            for c in candidates:
                self._apply_score(c, p_dwell=0.0, p_share=0.0, p_action=0.0)
            return sorted(candidates, key=lambda c: c.score.final_score, reverse=True)

        tasks = [self._score_single(candidate) for candidate in candidates]
        await asyncio.gather(*tasks)
        return sorted(candidates, key=lambda c: c.score.final_score, reverse=True)

    async def _score_single(self, candidate: Candidate) -> None:
        prompt = prompt_registry.get("algorithm.semantic_scoring")
        prompt_text = prompt.render(content=(candidate.content or "")[:2000])

        p_dwell = 0.0
        p_share = 0.0
        p_action = 0.0
        raw_response_preview = ""

        try:
            gemini_client = self.gemini_client
            if gemini_client is None:
                raise RuntimeError("gemini_client가 필요합니다.")

            response_text = await gemini_client.generate_content_async(prompt_text)
            raw_response_preview = (response_text or "")[:500]
            if not response_text:
                raise ValueError("빈 응답을 수신했습니다.")

            data = validate_json_output(
                response_text,
                required_fields=["p_dwell", "p_share", "p_action"],
            )
            if "error" in data:
                raise ValueError(data.get("error"))
            if "_validation_warning" in data:
                raise ValueError(data.get("_validation_warning"))

            p_dwell = self._to_prob(data.get("p_dwell"))
            p_share = self._to_prob(data.get("p_share"))
            p_action = self._to_prob(data.get("p_action"))

        except Exception as e:
            logger.error(f"SemanticScorer 실패 ({candidate.id}): {e}")
            candidate.metadata["semantic_scorer_error"] = str(e)
            candidate.metadata["semantic_scorer_raw"] = raw_response_preview

        self._apply_score(candidate, p_dwell=p_dwell, p_share=p_share, p_action=p_action)

    def _apply_score(self, candidate: Candidate, *, p_dwell: float, p_share: float, p_action: float) -> None:
        final_score = (p_dwell * 0.5) + (p_share * 0.3) + (p_action * 0.2)
        is_slop = final_score < self.SLOP_THRESHOLD

        candidate.is_slop = is_slop
        candidate.metadata["semantic_probabilities"] = {
            "p_dwell": p_dwell,
            "p_share": p_share,
            "p_action": p_action,
        }

        candidate.score = CandidateScore(
            final_score=round(float(final_score), 4),
            raw_score=round(float(final_score), 4),
            positive_score=round(float(final_score), 4),
            negative_score=0.0,
            weighted_components={
                "p_dwell": round(float(p_dwell), 4),
                "p_share": round(float(p_share), 4),
                "p_action": round(float(p_action), 4),
            },
            explanation=(
                f"Semantic score={final_score:.3f} "
                f"(dwell={p_dwell:.2f}, share={p_share:.2f}, action={p_action:.2f})"
            ),
        )

        logger.info(
            "SemanticScorer result "
            f"id={candidate.id} score={candidate.score.final_score:.4f} "
            f"p_dwell={p_dwell:.4f} p_share={p_share:.4f} p_action={p_action:.4f} "
            f"is_slop={candidate.is_slop}"
        )

    def _to_prob(self, value: Any) -> float:
        try:
            f = float(value)
        except (TypeError, ValueError):
            return 0.0
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return max(0.0, min(1.0, f))


class EngagementScorer:
    """
    X-Algorithm의 Weighted Scoring 로직 구현
    Gemini를 통해 19개 사용자 행동 확률을 예측하고 가중치 합산 점수를 산출합니다.
    """

    WEIGHTS: ClassVar[dict[str, float]] = {
        "purchase_intent": 10.0,
        "constructive_feedback": 5.0,
        "reply_inducing": 3.0,
        "share_probability": 8.0,
        "viral_potential": 7.0,
        "actionable_insight": 6.0,
        "quote_worthy": 4.0,
        "save_worthy": 5.0,
        "follow_author": 4.0,
        "dwell_time": 15.0,  # X-Algorithm에서 중요도 상승 보정
        "dm_probability": 3.0,
        "copy_link_probability": 4.0,
        "profile_click": 3.0,
        "bookmark_worthy": 5.0,
        # CandidateFeatures에 존재하나 기존 WEIGHTS에서 누락되어 있었음 (19개 시그널 정합)
        "sentiment_intensity": 2.0,
        "toxicity": -100.0,
        "controversy_score": -10.0,
        "not_interested": -15.0,
        "report_probability": -50.0,
    }

    NEGATIVE_OFFSET_RATIO: ClassVar[float] = 0.5

    def __init__(self, gemini_client: IMarketingAIService | None = None):
        # DI 컨테이너에서 주입되는 GeminiClient는 IMarketingAIService 프로토콜을 만족한다.
        self.gemini_client = gemini_client

    async def score(
        self, candidates: list[Candidate], context: dict[str, Any] | None = None
    ) -> list[Candidate]:
        """모든 후보군에 대해 AI 기반 점수 산정 및 정렬 (병렬 처리 최적화)"""
        if not candidates:
            return []
        context = context or {}

        # AI 클라이언트가 없으면(테스트/로컬) 기본 점수만 계산
        if self.gemini_client is None:
            for candidate in candidates:
                self._calculate_single_candidate(candidate)
            return sorted(candidates, key=lambda c: c.score.final_score, reverse=True)

        # 1. 모든 후보군에 대해 병렬로 AI 분석 수행 (처리 속도 대폭 개선)
        tasks = [self._predict_behavioral_probabilities(candidate, context) for candidate in candidates]
        await asyncio.gather(*tasks)

        # 2. 가중치 합산 점수 계산
        for candidate in candidates:
            self._calculate_single_candidate(candidate)

        # 3. 최종 점수 기반 정렬 (설명 로그 포함)
        return sorted(candidates, key=lambda c: c.score.final_score, reverse=True)

    async def _predict_behavioral_probabilities(
        self, candidate: Candidate, context: dict[str, Any] | None = None
    ) -> None:
        """Gemini 전용 프롬프트를 사용하여 19개 행동 시그널 분석 (Retry 및 Validation 강화)"""
        prompt = prompt_registry.get("algorithm.scoring")
        context = context or {}

        # 프롬프트 입력 데이터 구성
        input_data = {
            "metadata": f"Title: {candidate.title}, Category: {candidate.category}",
            "content": candidate.content[:1500] if candidate.content else "No content", # 토큰 절약
            "brand_guidelines": context.get("brand_guidelines", "General high-quality brand tone"),
            "insights": context.get("insights", "No specific insights provided")
        }

        try:
            prompt_text = prompt.render(**input_data)
            gemini_client = self.gemini_client
            if gemini_client is None:
                raise RuntimeError("gemini_client가 필요합니다.")

            response_text = await gemini_client.generate_content_async(prompt_text)
            if not response_text:
                raise ValueError("빈 응답을 수신했습니다.")

            response = validate_json_output(response_text, required_fields=["probabilities"])
            if "error" in response:
                raise ValueError(response.get("error"))

            probs = response.get("probabilities", {}) or {}

            # 예측된 확률값 업데이트 (Pydantic 모델 구조에 따라 안전하게 설정)
            valid_keys = 0
            for key, value in probs.items():
                if hasattr(candidate.features, key):
                    setattr(candidate.features, key, float(value))
                    valid_keys += 1

            candidate.metadata["ai_reasoning"] = response.get("reasoning_summary", "")

            if valid_keys < 10:
                logger.warning(f"AI 응답 데이터 부족: {candidate.id} (수신된 필드: {valid_keys})")

        except Exception as e:
            # 실패 시 로깅 강화 및 최소 기본값 유지
            logger.error(f"AI 스코어링 실패 ({candidate.id}): {e}")
            candidate.metadata["ai_error"] = str(e)
            # AI 분석이 실패했다는 사실을 랭킹 로직이 알 수 있도록 마킹
            candidate.score.explanation = "[AI 분석 지연] "

    def _calculate_single_candidate(self, candidate: Candidate) -> None:
        features = candidate.features
        score_components = {}
        positive_score = 0.0
        negative_score = 0.0
        reasons = []

        # Feature 기반 가중치 합산
        for feature_name, weight in self.WEIGHTS.items():
            probability = getattr(features, feature_name, 0.0)
            if weight == 0 or probability == 0:
                continue

            component_score = weight * probability
            score_components[feature_name] = round(component_score, 2)

            if component_score >= 0:
                positive_score += component_score
            else:
                negative_score += abs(component_score)

            if abs(component_score) > 1.5:
                effect = "높여" if component_score > 0 else "낮춰"
                reasons.append(f"{feature_name}({probability:.1f})가 점수를 {effect}줌")

        # Score Offsetting
        if negative_score > positive_score:
            excess = negative_score - positive_score
            adjusted_negative = positive_score + excess * self.NEGATIVE_OFFSET_RATIO
        else:
            adjusted_negative = negative_score

        raw_score = positive_score - adjusted_negative

        # Engagement boost (기존 성과 가중치)
        engagement_boost = min(math.log1p(candidate.like_count or 0) * 1.5, 5.0)
        if engagement_boost > 0:
            raw_score += engagement_boost
            score_components["engagement_boost"] = round(engagement_boost, 2)

        candidate.score = CandidateScore(
            final_score=round(raw_score, 2),
            raw_score=round(positive_score - negative_score, 2),
            positive_score=round(positive_score, 2),
            negative_score=round(negative_score, 2),
            weighted_components=score_components,
            explanation=", ".join(reasons) if reasons else "일반적인 댓글",
        )
