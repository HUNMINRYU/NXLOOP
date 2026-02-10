import asyncio
import hashlib

from api import validate_json_output
from core.interfaces.ai_service import IMarketingAIService
from core.prompts import prompt_registry
from services.pipeline.types import Candidate, CandidateFeatures
from utils.cache import TTLCache
from utils.logger import get_logger, log_feature_end, log_feature_start, log_llm_fail

logger = get_logger(__name__)

MAX_CONCURRENT_REQUESTS = 5
_feature_cache = TTLCache(default_ttl=86400)


class FeatureHydrator:
    """
    X-Algorithm의 Hydration 단계 (LLM Feature Extraction)
    단순 댓글 텍스트 -> Rich Feature (구매의도, 바이럴 가능성 등) 변환
    """

    def __init__(self, gemini_client: IMarketingAIService):
        self.gemini_client = gemini_client

    async def hydrate(self, candidates: list[Candidate]) -> list[Candidate]:
        """Gemini를 통해 댓글들의 Feature를 배치로 추출"""
        if not candidates:
            return []

        log_feature_start("xalgo_hydration_llm", f"candidates={len(candidates)}")

        # 1. 캐시 확인 및 처리할 대상 선별
        to_hydrate: list[tuple[int, Candidate]] = []
        for idx, c in enumerate(candidates):
            cache_key = hashlib.md5(c.content.encode("utf-8")).hexdigest()
            cached = _feature_cache.get(cache_key)
            if cached:
                c.features = CandidateFeatures(**cached)
            else:
                to_hydrate.append((idx, c))

        if not to_hydrate:
            log_feature_end("xalgo_hydration_llm", extra_detail="all_cached")
            return candidates

        # 2. 배치 처리 (5개씩 묶음)
        batch_size = 5
        batches = [
            to_hydrate[i : i + batch_size]
            for i in range(0, len(to_hydrate), batch_size)
        ]

        # 동시 배치 요청 제한
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        async def process_batch(batch_items: list[tuple[int, Candidate]]):
            async with semaphore:
                await self._analyze_batch(batch_items)

        tasks = [process_batch(b) for b in batches]
        await asyncio.gather(*tasks)

        success_count = sum(1 for c in candidates if c.features.keywords)
        logger.info(f"Hydration 완료: 성공={success_count}/{len(candidates)}")
        log_feature_end(
            "xalgo_hydration_llm",
            extra_detail=f"cache_hit={len(candidates) - len(to_hydrate)} miss={len(to_hydrate)} success={success_count}",
        )
        return candidates

    async def _analyze_batch(self, batch_items: list[tuple[int, Candidate]]) -> None:
        """한 배치의 댓글들을 분석하고 각 Candidate에 결과 주입"""
        # 프롬프트 입력용 인덱싱 텍스트 생성
        # 예: "0: 내용1\n1: 내용2\n..."
        comments_with_index = "\n".join(
            [f"{idx}: {c.content}" for idx, c in batch_items]
        )

        prompt = prompt_registry.get("hydration.feature_extraction").render(
            comments_with_index=comments_with_index
        )

        try:
            response_text = await self.gemini_client.generate_content_async(prompt)
            if not response_text:
                raise ValueError("빈 응답을 수신했습니다.")

            data = validate_json_output(response_text, required_fields=["results"])
            if "error" in data:
                raise ValueError(data.get("error"))

            results = data.get("results", [])
            # 인덱스 기반 매핑 (batch_items는 (original_idx, candidate) 튜플)
            # original_idx를 key로 하고 candidate를 value로 하는 맵 생성
            item_map = dict(batch_items)

            for res in results:
                idx = res.get("index")
                features_data = res.get("features")
                if idx is None or not features_data or idx not in item_map:
                    continue

                candidate = item_map[idx]
                features = CandidateFeatures(
                    purchase_intent=features_data.get("purchase_intent", 0.0),
                    constructive_feedback=features_data.get(
                        "constructive_feedback", 0.0
                    ),
                    reply_inducing=features_data.get("reply_inducing", 0.0),
                    share_probability=features_data.get("share_probability", 0.0),
                    viral_potential=features_data.get("viral_potential", 0.0),
                    actionable_insight=features_data.get("actionable_insight", 0.0),
                    quote_worthy=features_data.get("quote_worthy", 0.0),
                    save_worthy=features_data.get("save_worthy", 0.0),
                    follow_author=features_data.get("follow_author", 0.0),
                    sentiment_intensity=features_data.get("sentiment_intensity", 0.0),
                    dwell_time=features_data.get("dwell_time", 0.0),
                    toxicity=features_data.get("toxicity", 0.0),
                    controversy_score=features_data.get("controversy_score", 0.0),
                    not_interested=features_data.get("not_interested", 0.0),
                    report_probability=features_data.get("report_probability", 0.0),
                    dm_probability=features_data.get("dm_probability", 0.0),
                    copy_link_probability=features_data.get(
                        "copy_link_probability", 0.0
                    ),
                    profile_click=features_data.get("profile_click", 0.0),
                    bookmark_worthy=features_data.get("bookmark_worthy", 0.0),
                    keywords=features_data.get("keywords", []),
                    topics=features_data.get("topics", []),
                )
                candidate.features = features

                # 캐시 저장
                cache_key = hashlib.md5(candidate.content.encode("utf-8")).hexdigest()
                _feature_cache.set(
                    cache_key,
                    features.__dict__ if hasattr(features, "__dict__") else {},
                )

        except Exception as e:
            log_llm_fail("Hydration 배치 분석", str(e))
            logger.warning(f"Hydration 배치 분석 실패: {e}")
