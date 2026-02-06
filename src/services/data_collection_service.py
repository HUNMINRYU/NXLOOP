"""
데이터 수집 서비스
YouTube + Naver + X-Algorithm 인사이트 수집
"""

import asyncio
from collections.abc import Callable

from core.models import CollectedData, PipelineConfig, PipelineStep
from services.data_validator import validate_comments
from services.market_trend_service import MarketTrendService
from services.naver_service import NaverService
from services.pipeline.orchestrator import PipelineOrchestrator
from services.youtube_service import YouTubeService
from utils.logger import get_logger, log_error, log_info, log_step

logger = get_logger(__name__)


class DataCollectionService:
    """데이터 수집 통합 서비스"""

    def __init__(
        self,
        youtube_service: YouTubeService,
        naver_service: NaverService,
        pipeline_orchestrator: PipelineOrchestrator,
        market_trend_service: MarketTrendService | None = None,
    ) -> None:
        self._youtube = youtube_service
        self._naver = naver_service
        self._orchestrator = pipeline_orchestrator
        self._market_trend = market_trend_service

    def collect_all_data(
        self,
        product: dict,
        config: PipelineConfig,
        progress_callback: Callable[[PipelineStep, str], None] | None = None,
    ) -> CollectedData:
        """전체 데이터 수집 (동기 래퍼).

        주의: 비동기 컨텍스트(이미 실행 중인 이벤트 루프)에서는 이 메서드를 직접 호출하지 말고
        `collect_all_data_async()`를 사용해야 합니다.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self.collect_all_data_async(
                    product=product,
                    config=config,
                    progress_callback=progress_callback,
                )
            )

        raise RuntimeError(
            "동작 중인 이벤트 루프에서 collect_all_data()를 호출할 수 없습니다. "
            "collect_all_data_async()를 사용하세요."
        )

    async def collect_all_data_async(
        self,
        product: dict,
        config: PipelineConfig,
        progress_callback: Callable[[PipelineStep, str], None] | None = None,
    ) -> CollectedData:
        """전체 데이터 수집 (비동기).

        외부 API 호출은 동기 구현이므로 thread offload로 실행하고,
        X-Algorithm(오케스트레이터) 분석은 async로 그대로 await 합니다.
        """
        p_name = product.get("name", "N/A")
        log_step("데이터 수집", "시작", f"제품: {p_name}")

        collected_data = CollectedData()

        if progress_callback:
            progress_callback(PipelineStep.YOUTUBE_COLLECTION, "YouTube 데이터 수집 중...")

        # NOTE: 현재 실행 환경에서 `asyncio.to_thread()`/`run_in_executor()`가 정상 동작하지 않는
        # 문제가 있어, 동기 호출로 처리합니다.
        youtube_data = self._youtube.collect_product_data(
            product=product,
            max_results=config.youtube_count,
            include_comments=config.include_comments,
        )
        collected_data.youtube_data = youtube_data
        collected_data.pain_points = youtube_data.get("pain_points", [])
        collected_data.gain_points = youtube_data.get("gain_points", [])

        if progress_callback:
            progress_callback(PipelineStep.NAVER_COLLECTION, "네이버 쇼핑 데이터 수집 중...")

        naver_data = self._naver.collect_product_data(
            product=product,
            max_results=config.naver_count,
        )
        collected_data.naver_data = naver_data

        if self._market_trend:
            if progress_callback:
                progress_callback(PipelineStep.DATA_COLLECTION, "시장 동향 수집 중...")
            collected_data.market_trends = self._market_trend.get_market_trends(product)

        # YouTube 비디오 목록 저장
        if youtube_data and "videos" in youtube_data:
            collected_data.youtube_videos = youtube_data["videos"]

        if progress_callback:
            progress_callback(PipelineStep.COMMENT_ANALYSIS, "X-Algorithm 인사이트 분석 중...")

        try:
            comments: list[dict] = []
            if youtube_data and "videos" in youtube_data:
                for v in youtube_data["videos"]:
                    for c in v.get("comments", []):
                        comments.append(
                            {
                                "author": c.get("author", "unknown"),
                                "text": c.get("text", ""),
                                "likes": c.get("likes", 0),
                            }
                        )

            if not comments and youtube_data:
                for c in youtube_data.get("top_comments", []):
                    comments.append(
                        {
                            "author": c.get("author", "unknown"),
                            "text": c.get("text", ""),
                            "likes": c.get("likes", 0),
                        }
                    )

            seen_texts: set[str] = set()
            unique_comments: list[dict] = []
            for c in comments:
                text = str(c.get("text", "")).strip()
                if not text or text in seen_texts:
                    continue
                seen_texts.add(text)
                unique_comments.append(c)

            unique_comments.sort(key=lambda x: x.get("likes", 0), reverse=True)
            limited_comments = unique_comments[: config.max_comment_samples]

            log_info(
                f"X-Algorithm 댓글 샘플링: {len(limited_comments)}/{len(unique_comments)}"
            )

            validated, quality_report = validate_comments(limited_comments)
            collected_data.quality_report = quality_report.model_dump()
            log_info(
                f"데이터 품질: {quality_report.quality_score:.1%} "
                f"({quality_report.valid_count}/{quality_report.total_count})"
            )

            validated_payload = [item.model_dump() for item in validated]
            analysis_result = await self._orchestrator.run_pipeline(validated_payload)
            collected_data.top_insights = analysis_result.get("insights", [])
            log_info(
                f"X-Algorithm 분석 완료: {len(collected_data.top_insights)}개 인사이트 도출"
            )
        except Exception as e:
            logger.error(f"X-Algorithm 분석 실패: {e}")
            log_error(f"X-Algorithm 분석 중 오류 발생: {e}")

        if progress_callback:
            progress_callback(PipelineStep.DATA_COLLECTION, "데이터 수집 완료")

        return collected_data

    # NOTE: 기존 `_run_async()` 구현은 sync 코드에서 async 코드를 억지로 실행하기 위한 보조였으나,
    # `asyncio.to_thread()`와 결합될 때 완료 신호 전달이 멈추는 문제가 있어 제거했습니다.
