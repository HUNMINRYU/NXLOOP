"""
CTR 예측 서비스
썸네일 + 제목 조합 분석 및 클릭률 예측
"""

from core.prompts import (
    prompt_registry,
)
from services.model_evaluator import ModelEvaluator
from utils.logger import (
    get_logger,
    log_llm_fail,
    log_llm_request,
    log_llm_response,
    log_step,
    log_success,
)

logger = get_logger(__name__)


class CTRPredictor:
    """AI 기반 CTR 예측 서비스"""

    def __init__(self, gemini_client=None) -> None:
        """
        Args:
            gemini_client: AI 기반 심층 분석 시 사용 (선택)
        """
        self._gemini = gemini_client
        self._evaluator = ModelEvaluator()

    def predict_ctr(
        self,
        title: str,
        thumbnail_description: str = "",
        competitor_titles: list[str] | None = None,
        category: str = "general",
    ) -> dict:
        """
        제목과 썸네일 조합의 예상 CTR 계산

        Args:
            title: 영상 제목
            thumbnail_description: 썸네일 설명 (또는 분석 결과)
            competitor_titles: 경쟁 영상 제목들
            category: 카테고리

        Returns:
            CTR 예측 결과 딕셔너리
        """
        log_step("CTR 예측", "시작", f"제목: {title[:30]}...")

        scores = {}

        # 1. 제목 길이 점수
        scores["title_length"] = self._score_title_length(title)

        # 2. 이모지 사용 점수
        scores["emoji_usage"] = self._score_emoji_usage(title)

        # 3. 후킹 강도 점수
        scores["hook_strength"] = self._score_hook_strength(title)

        # 4. 썸네일 요소 점수 (설명 기반 추정)
        scores["thumbnail"] = self._score_thumbnail(thumbnail_description)

        # 5. 경쟁사 대비 차별화 점수
        scores["differentiation"] = self._score_differentiation(
            title, competitor_titles or []
        )

        # 가중 평균 계산
        total_score = (
            scores["title_length"] * 0.15
            + scores["emoji_usage"] * 0.10
            + scores["hook_strength"] * 0.25
            + scores["thumbnail"] * 0.30
            + scores["differentiation"] * 0.20
        )

        # CTR 범위로 변환 (2% ~ 15%)
        predicted_ctr = 2 + (total_score / 100) * 13

        result = {
            "predicted_ctr": round(predicted_ctr, 2),
            "ctr_range": self._get_ctr_range(predicted_ctr),
            "total_score": round(total_score, 1),
            "breakdown": scores,
            "recommendations": self._generate_recommendations(scores),
            "grade": self._get_grade(total_score),
        }

        log_success(f"CTR 예측 완료: {result['predicted_ctr']}% ({result['grade']})")
        self._evaluator.log_prediction(
            model_name="ctr_hybrid",
            input_data={"title": title, "thumbnail_description": thumbnail_description},
            output=result,
        )
        return result

    def _score_title_length(self, title: str) -> float:
        """제목 길이 점수 (0-100)"""
        length = len(title)
        optimal_min, optimal_max = 30, 60

        if optimal_min <= length <= optimal_max:
            return 100.0
        elif length < optimal_min:
            return max(0, 100 - (optimal_min - length) * 3)
        else:
            return max(0, 100 - (length - optimal_max) * 2)

    def _score_emoji_usage(self, title: str) -> float:
        """이모지 사용 점수 (0-100)"""
        import re

        # 이모지 패턴
        emoji_pattern = re.compile(
            "["
            "\U0001f600-\U0001f64f"  # emoticons
            "\U0001f300-\U0001f5ff"  # symbols & pictographs
            "\U0001f680-\U0001f6ff"  # transport & map
            "\U0001f1e0-\U0001f1ff"  # flags
            "\U00002702-\U000027b0"
            "\U000024c2-\U0001f251"
            "]+",
            flags=re.UNICODE,
        )

        emojis = emoji_pattern.findall(title)
        count = len(emojis)

        if count == 0:
            return 60.0  # 이모지 없음 - 보통
        elif 1 <= count <= 3:
            return 100.0  # 최적
        elif count <= 5:
            return 80.0  # 약간 많음
        else:
            return 50.0  # 너무 많음

    def _score_hook_strength(self, title: str) -> float:
        """후킹 강도 점수 (0-100)"""
        strong_hooks = ["비밀", "충격", "반전", "꿀팁", "필수", "주의", "경고", "긴급"]
        medium_hooks = ["방법", "이유", "진실", "사실", "효과", "결과", "비교"]
        weak_hooks = ["추천", "소개", "리뷰", "후기"]

        title_lower = title.lower()

        # 강한 후킹 키워드 체크
        strong_count = sum(1 for h in strong_hooks if h in title_lower)
        medium_count = sum(1 for h in medium_hooks if h in title_lower)
        weak_count = sum(1 for h in weak_hooks if h in title_lower)

        score = 50.0  # 기본
        score += strong_count * 20
        score += medium_count * 10
        score += weak_count * 5

        # 숫자 사용 보너스 (예: "3가지 방법")
        if any(c.isdigit() for c in title):
            score += 10

        # 물음표 사용 보너스
        if "?" in title:
            score += 5

        return min(100.0, score)

    def _score_thumbnail(self, description: str) -> float:
        """썸네일 점수 (설명 기반 추정)"""
        if not description:
            return 70.0  # 설명 없으면 평균

        score = 50.0
        desc_lower = description.lower()

        # 긍정적 요소
        if any(word in desc_lower for word in ["얼굴", "face", "인물", "사람"]):
            score += 15
        if any(word in desc_lower for word in ["텍스트", "text", "글자"]):
            score += 10
        if any(word in desc_lower for word in ["밝은", "bright", "선명", "contrast"]):
            score += 10
        if any(word in desc_lower for word in ["화살표", "arrow", "강조"]):
            score += 5
        if any(word in desc_lower for word in ["before", "after", "비교", "전후"]):
            score += 10

        return min(100.0, score)

    def _score_differentiation(self, title: str, competitor_titles: list[str]) -> float:
        """경쟁사 대비 차별화 점수"""
        if not competitor_titles:
            return 75.0  # 비교 대상 없음

        # 제목 유사도 계산 (간단한 키워드 겹침)
        title_words = set(title.lower().split())

        similarity_scores = []
        for comp_title in competitor_titles[:5]:
            comp_words = set(comp_title.lower().split())
            if title_words and comp_words:
                overlap = len(title_words & comp_words) / len(title_words | comp_words)
                similarity_scores.append(overlap)

        if not similarity_scores:
            return 75.0

        avg_similarity = sum(similarity_scores) / len(similarity_scores)

        # 차별화 점수 (유사도가 낮을수록 높음)
        differentiation = (1 - avg_similarity) * 100
        return max(50.0, min(100.0, differentiation))

    def _get_ctr_range(self, ctr: float) -> str:
        """CTR 범위 레이블"""
        if ctr >= 10:
            return "매우 높음 (상위 5%)"
        elif ctr >= 7:
            return "높음 (상위 20%)"
        elif ctr >= 5:
            return "평균 (50%)"
        elif ctr >= 3:
            return "낮음 (하위 30%)"
        else:
            return "매우 낮음 (하위 10%)"

    def _get_grade(self, score: float) -> str:
        """점수 기반 등급"""
        if score >= 90:
            return "S"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        else:
            return "D"

    def _generate_recommendations(self, scores: dict) -> list[str]:
        """개선 권장사항 생성"""
        recommendations = []

        if scores.get("title_length", 100) < 70:
            recommendations.append("📏 제목 길이를 30-60자 사이로 조정하세요")

        if scores.get("emoji_usage", 100) < 70:
            recommendations.append("😊 이모지 1-3개를 추가하여 눈에 띄게 만드세요")

        if scores.get("hook_strength", 100) < 70:
            recommendations.append(
                "🎣 '비밀', '꿀팁', '필수' 같은 후킹 키워드를 추가하세요"
            )

        if scores.get("thumbnail", 100) < 70:
            recommendations.append("🖼️ 썸네일에 얼굴/대비/텍스트 오버레이를 추가하세요")

        if scores.get("differentiation", 100) < 70:
            recommendations.append("💡 경쟁 영상과 차별화된 앵글을 시도하세요")

        if not recommendations:
            recommendations.append("✅ 모든 요소가 최적화되어 있습니다!")

        return recommendations

    def predict_with_pipeline_insights(
        self,
        title: str,
        thumbnail_description: str = "",
        pipeline_insights: list[dict] | None = None,
        category: str = "general",
    ) -> dict:
        """
        파이프라인 결과(top insights)를 CTR 예측에 반영.
        adjusted_ctr = base_ctr * (1 + Σ(weight_i × signal_i))
        """
        basic = self.predict_ctr(title, thumbnail_description, category=category)

        if not pipeline_insights:
            return basic

        # 파이프라인 insight에서 시그널 추출 및 가중치 적용
        signal_weights = {
            "purchase_intent": 0.15,
            "viral_potential": 0.10,
            "share_probability": 0.08,
            "reply_inducing": 0.05,
            "bookmark_worthy": 0.07,
            "constructive_feedback": 0.05,
        }

        adjustment = 0.0
        signal_details = {}
        for insight in pipeline_insights:
            features = insight.get("features", {})
            for signal_name, weight in signal_weights.items():
                value = features.get(signal_name, 0.0)
                if value > 0:
                    contribution = weight * value
                    adjustment += contribution
                    signal_details[signal_name] = round(contribution, 4)

        # 조정 범위 제한 (-30% ~ +50%)
        adjustment = max(-0.3, min(0.5, adjustment))

        adjusted_ctr = basic["predicted_ctr"] * (1 + adjustment)
        adjusted_ctr = max(1.0, min(20.0, adjusted_ctr))  # 합리적 범위 제한

        basic["pipeline_adjusted_ctr"] = round(adjusted_ctr, 2)
        basic["pipeline_adjustment"] = round(adjustment * 100, 1)
        basic["pipeline_signals"] = signal_details

        return basic

    def compare_variations(self, variations: list[dict]) -> list[dict]:
        """
        여러 버전의 제목/썸네일 비교

        Args:
            variations: [{title, thumbnail_description, ...}] 리스트

        Returns:
            예측 결과 + 순위 리스트
        """
        results = []

        for i, var in enumerate(variations):
            prediction = self.predict_ctr(
                title=var.get("title", ""),
                thumbnail_description=var.get("thumbnail_description", ""),
            )
            prediction["variation_id"] = i + 1
            prediction["title"] = var.get("title", "")
            results.append(prediction)

        # CTR 순으로 정렬
        results.sort(key=lambda x: x["predicted_ctr"], reverse=True)

        # 순위 추가
        for rank, result in enumerate(results, 1):
            result["rank"] = rank

        return results

    async def predict_with_ai(
        self,
        title: str,
        category: str = "general",
        top_insights: list[dict] | None = None,
    ) -> dict:
        """
        AI를 활용한 심층 CTR 예측

        Args:
            title: 영상 제목
            category: 카테고리
            top_insights: X-Algorithm 핵심 인사이트

        Returns:
            AI 분석 포함 예측 결과
        """
        # 기본 예측 먼저 수행
        basic_prediction = self.predict_ctr(title)

        if not self._gemini:
            return basic_prediction

        insights_text = ""
        if top_insights:
            import json

            insights_text = f"\n## X-Algorithm 핵심 인사이트 (참고용)\n{json.dumps(top_insights, ensure_ascii=False, indent=2)}\n"

        prompt = prompt_registry.get("ctr.prediction").render(
            insights_text=insights_text,
            title=title,
            category=category,
        )
        log_llm_request("CTR AI 분석", f"제목: {title[:30]}...")

        try:
            ai_response = await self._gemini.generate_content_async(prompt)
            log_llm_response("CTR AI 분석", f"응답 {len(ai_response or '')}자")
            basic_prediction["ai_analysis"] = ai_response
            return basic_prediction
        except Exception as e:
            log_llm_fail("CTR AI 분석", str(e))
            logger.warning(f"AI CTR 분석 실패: {e}")
            return basic_prediction
