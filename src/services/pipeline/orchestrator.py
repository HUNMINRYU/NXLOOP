from __future__ import annotations

import time
from typing import Any

from services.pipeline.side_effects import SideEffectManager
from services.pipeline.stages.diversity_scorer import MultiFactorDiversityScorer
from services.pipeline.stages.filter import QualityFilter
from services.pipeline.stages.hydration import FeatureHydrator
from services.pipeline.stages.scorer import SemanticScorer
from services.pipeline.stages.selector import TopInsightSelector
from services.pipeline.stages.source import CommentSource
from services.pipeline.types import Candidate
from utils.logger import get_logger

logger = get_logger(__name__)


class PipelineOrchestrator:
    """
    Nexloop X-Inspired Pipeline (NXP) Controller
    Source -> Hydrator -> Filter -> AI Scorer -> Diversity Scorer -> Selector

    각 단계별 소요 시간, 처리 건수, 필터링률 등 성능 메트릭을 자동 수집한다.
    """

    def __init__(
        self,
        source: CommentSource,
        hydrator: FeatureHydrator,
        quality_filter: QualityFilter,
        scorer: SemanticScorer,
        diversity_scorer: MultiFactorDiversityScorer,
        selector: TopInsightSelector,
        side_effects: SideEffectManager | None = None,
    ):
        self.source = source
        self.hydrator = hydrator
        self.filter = quality_filter
        self.scorer = scorer
        self.diversity_scorer = diversity_scorer
        self.selector = selector
        self.side_effects = side_effects or SideEffectManager()

    async def run_pipeline(
        self,
        raw_data: list[dict[str, Any]],
        pipeline_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """X 알고리즘 기반 파이프라인 전체 실행 (성능 메트릭 수집 포함)"""
        pipeline_start = time.monotonic()

        stats: dict[str, Any] = {}
        stage_timings: dict[str, float] = {}
        stage_counts: dict[str, dict[str, int]] = {}
        context = pipeline_context or {}

        # 1. Source: Raw Data -> Candidate 변환 (비동기 처리 최적화)
        t0 = time.monotonic()
        candidates = await self.source.item_to_candidate(
            raw_data, brand_context=context.get("brand_guidelines", "")
        )
        stage_timings["source"] = round(time.monotonic() - t0, 3)
        stats["original_count"] = len(candidates)
        stage_counts["source"] = {"input": len(raw_data), "output": len(candidates)}

        # 2-1. Pre-Filter
        pre_filter_input = len(candidates)
        t0 = time.monotonic()
        candidates = self._safe_stage("pre_filter", self.filter.filter, candidates)
        stage_timings["pre_filter"] = round(time.monotonic() - t0, 3)
        stage_counts["pre_filter"] = {
            "input": pre_filter_input,
            "output": len(candidates),
            "filtered": pre_filter_input - len(candidates),
        }

        # 2-2. Hydration (Feature Enrichment)
        hydration_input = len(candidates)
        t0 = time.monotonic()
        candidates = await self._safe_async_stage(
            "hydration", self.hydrator.hydrate, candidates
        )
        stage_timings["hydration"] = round(time.monotonic() - t0, 3)
        stage_counts["hydration"] = {
            "input": hydration_input,
            "output": len(candidates),
        }

        # 2-3. Post-Filter
        post_filter_input = len(candidates)
        t0 = time.monotonic()
        candidates = self._safe_stage("post_filter", self.filter.filter, candidates)
        stage_timings["post_filter"] = round(time.monotonic() - t0, 3)
        stats["hydrated_count"] = len(candidates)
        stage_counts["post_filter"] = {
            "input": post_filter_input,
            "output": len(candidates),
            "filtered": post_filter_input - len(candidates),
        }

        if not candidates:
            stats["stage_timings"] = stage_timings
            stats["stage_counts"] = stage_counts
            stats["total_duration"] = round(time.monotonic() - pipeline_start, 3)
            return {
                "insights": [],
                "stats": stats,
                "summary": "분석 가능한 데이터가 없습니다.",
            }

        # 3. AI Behavioral Scoring (X's Grok-style Multi-Objective Scoring)
        scoring_input = len(candidates)
        t0 = time.monotonic()
        ranked_candidates = await self._safe_async_stage(
            "scoring",
            lambda cands: self.scorer.score(cands, context),
            candidates,
        )
        stage_timings["scoring"] = round(time.monotonic() - t0, 3)
        stage_counts["scoring"] = {
            "input": scoring_input,
            "output": len(ranked_candidates),
        }

        # 4. Multi-Factor Diversity (Categorical & Semantic Diversity)
        diversity_input = len(ranked_candidates)
        t0 = time.monotonic()
        history_context = context.get("history", {})
        ranked_candidates = self._safe_stage(
            "diversity",
            lambda cands: self.diversity_scorer.apply(cands, history_context),
            ranked_candidates,
        )
        stage_timings["diversity"] = round(time.monotonic() - t0, 3)
        stage_counts["diversity"] = {
            "input": diversity_input,
            "output": len(ranked_candidates),
        }

        stats["processed_count"] = len(ranked_candidates)

        # 5. Selection: 최종 상위 결과물 선정
        t0 = time.monotonic()
        top_k = context.get("top_k", 5)
        selected_candidates = self.selector.select(ranked_candidates, top_k=top_k)
        stage_timings["selection"] = round(time.monotonic() - t0, 3)
        stage_counts["selection"] = {
            "input": len(ranked_candidates),
            "output": len(selected_candidates),
        }

        # ── 성능 메트릭 집계 ──────────────────────────────
        total_duration = round(time.monotonic() - pipeline_start, 3)
        total_filtered = (
            stage_counts.get("pre_filter", {}).get("filtered", 0)
            + stage_counts.get("post_filter", {}).get("filtered", 0)
        )
        filtering_rate = (
            round(total_filtered / stats["original_count"], 4)
            if stats["original_count"] > 0
            else 0.0
        )

        stats["stage_timings"] = stage_timings
        stats["stage_counts"] = stage_counts
        stats["total_duration"] = total_duration
        stats["total_filtered"] = total_filtered
        stats["filtering_rate"] = filtering_rate
        stats["result_count"] = len(selected_candidates)
        if total_duration > 0:
            stats["throughput_per_sec"] = round(
                stats["original_count"] / total_duration, 1
            )

        # AI 요약 생성 (X 알고리즘 통합 인사이트)
        total_reasoning = " ".join(
            [
                c.metadata.get("ai_reasoning", "")
                for c in selected_candidates
                if c.metadata.get("ai_reasoning")
            ]
        )
        summary = (
            total_reasoning[:500]
            if total_reasoning
            else "X 알고리즘 기반 고효율 후보군 선별 완료."
        )

        # Side effects 발송
        self.side_effects.emit(
            "pipeline_completed",
            stats=stats,
            result_count=len(selected_candidates),
        )

        logger.info(
            "파이프라인 완료: %d건 → %d건 (%.1f초, 필터링률 %.1f%%)",
            stats["original_count"],
            len(selected_candidates),
            total_duration,
            filtering_rate * 100,
            extra={
                "stage_timings": stage_timings,
                "total_duration": total_duration,
            },
        )

        return {
            "insights": self.selector.format_for_response(selected_candidates),
            "stats": stats,
            "summary": summary,
        }

    # --- 유틸리티 메서드 ---
    def _safe_stage(
        self, stage_name: str, fn: Any, candidates: list[Candidate]
    ) -> list[Candidate]:
        backup = list(candidates)
        try:
            return fn(candidates)
        except Exception as e:
            logger.error("%s 실패, backup 사용: %s", stage_name, e)
            self.side_effects.emit("stage_error", stage=stage_name, error=str(e))
            return backup

    async def _safe_async_stage(
        self, stage_name: str, fn: Any, candidates: list[Candidate]
    ) -> list[Candidate]:
        backup = list(candidates)
        try:
            return await fn(candidates)
        except Exception as e:
            logger.error("%s 실패, backup 사용: %s", stage_name, e)
            self.side_effects.emit("stage_error", stage=stage_name, error=str(e))
            return backup
