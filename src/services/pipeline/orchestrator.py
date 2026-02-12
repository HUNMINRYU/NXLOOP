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
from utils.logger import (
    get_logger,
    log_feature_end,
    log_feature_fail,
    log_feature_start,
)

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
        top_k = int((pipeline_context or {}).get("top_k", 5) or 5)
        # NOTE: 이 함수는 HTTP 핸들러가 아니지만, "지금 어떤 기능이 도는지"를 운영 로그에서
        # 빠르게 파악하기 위해 [FEATURE] 로깅을 추가한다. (docs/2026-02-08/cursor/logging-strategy.md)
        log_feature_start("pipeline_orchestrator_run", f"items={len(raw_data)} top_k={top_k}")

        stats: dict[str, Any] = {}
        stage_timings: dict[str, float] = {}
        stage_counts: dict[str, dict[str, int]] = {}
        context = pipeline_context or {}
        context["top_k"] = top_k

        try:
            # 1. Source: Raw Data -> Candidate 변환 (비동기 처리 최적화)
            t0 = time.monotonic()
            log_feature_start("xalgo_source", f"raw_items={len(raw_data)}")
            candidates = await self.source.item_to_candidate(
                raw_data, brand_context=context.get("brand_guidelines", "")
            )
            stage_timings["source"] = round(time.monotonic() - t0, 3)
            stats["original_count"] = len(candidates)
            stage_counts["source"] = {"input": len(raw_data), "output": len(candidates)}
            log_feature_end(
                "xalgo_source",
                duration_sec=stage_timings["source"],
                extra_detail=f"candidates={len(candidates)}",
            )

            # 2-1. Pre-Filter
            pre_filter_input = len(candidates)
            t0 = time.monotonic()
            log_feature_start("xalgo_pre_filter", f"in={pre_filter_input}")
            candidates = self._safe_stage("pre_filter", self.filter.filter, candidates)
            stage_timings["pre_filter"] = round(time.monotonic() - t0, 3)
            pii_masked = sum(
                1 for c in candidates if bool((c.metadata or {}).get("pii_masked"))
            )
            stage_counts["pre_filter"] = {
                "input": pre_filter_input,
                "output": len(candidates),
                "filtered": pre_filter_input - len(candidates),
            }
            log_feature_end(
                "xalgo_pre_filter",
                duration_sec=stage_timings["pre_filter"],
                extra_detail=(
                    f"out={len(candidates)} filtered={pre_filter_input - len(candidates)} "
                    f"pii_masked={pii_masked}"
                ),
            )

            # 2-2. Hydration (Feature Enrichment)
            hydration_input = len(candidates)
            t0 = time.monotonic()
            log_feature_start("xalgo_hydration", f"in={hydration_input}")
            candidates = await self._safe_async_stage(
                "hydration", self.hydrator.hydrate, candidates
            )
            stage_timings["hydration"] = round(time.monotonic() - t0, 3)
            hydrated_with_keywords = sum(
                1 for c in candidates if bool(getattr(c.features, "keywords", None))
            )
            stage_counts["hydration"] = {
                "input": hydration_input,
                "output": len(candidates),
            }
            log_feature_end(
                "xalgo_hydration",
                duration_sec=stage_timings["hydration"],
                extra_detail=f"out={len(candidates)} keywords={hydrated_with_keywords}",
            )

            # 2-3. Post-Filter
            post_filter_input = len(candidates)
            t0 = time.monotonic()
            log_feature_start("xalgo_post_filter", f"in={post_filter_input}")
            candidates = self._safe_stage("post_filter", self.filter.filter, candidates)
            stage_timings["post_filter"] = round(time.monotonic() - t0, 3)
            stats["hydrated_count"] = len(candidates)
            stage_counts["post_filter"] = {
                "input": post_filter_input,
                "output": len(candidates),
                "filtered": post_filter_input - len(candidates),
            }
            log_feature_end(
                "xalgo_post_filter",
                duration_sec=stage_timings["post_filter"],
                extra_detail=f"out={len(candidates)} filtered={post_filter_input - len(candidates)}",
            )

            if not candidates:
                stats["stage_timings"] = stage_timings
                stats["stage_counts"] = stage_counts
                stats["total_duration"] = round(time.monotonic() - pipeline_start, 3)
                log_feature_end(
                    "pipeline_orchestrator_run",
                    duration_sec=stats["total_duration"],
                    extra_detail="no_candidates_after_filter",
                )
                return {
                    "insights": [],
                    "stats": stats,
                    "summary": "분석 가능한 데이터가 없습니다.",
                }

            # 3. AI Behavioral Scoring (X's Grok-style Multi-Objective Scoring)
            scoring_input = len(candidates)
            t0 = time.monotonic()
            log_feature_start("xalgo_scoring", f"in={scoring_input}")
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
            slop_count = sum(1 for c in ranked_candidates if bool(getattr(c, "is_slop", False)))
            if ranked_candidates:
                scores = [float(c.score.final_score) for c in ranked_candidates if c.score]
                min_score = min(scores) if scores else 0.0
                max_score = max(scores) if scores else 0.0
            else:
                min_score = 0.0
                max_score = 0.0
            log_feature_end(
                "xalgo_scoring",
                duration_sec=stage_timings["scoring"],
                extra_detail=f"out={len(ranked_candidates)} slop={slop_count} score_range={min_score:.3f}..{max_score:.3f}",
            )

            # 4. Multi-Factor Diversity (Categorical & Semantic Diversity)
            diversity_input = len(ranked_candidates)
            t0 = time.monotonic()
            log_feature_start("xalgo_diversity", f"in={diversity_input}")
            history_context = context.get("history", {})
            ranked_candidates = self._safe_stage(
                "diversity",
                lambda cands: self.diversity_scorer.apply(cands, history_context),
                ranked_candidates,
            )
            stage_timings["diversity"] = round(time.monotonic() - t0, 3)
            diversity_adjusted = sum(
                1
                for c in ranked_candidates
                if isinstance(getattr(c, "score", None), object)
                and isinstance(getattr(c.score, "weighted_components", None), dict)
                and ("diversity_multiplier" in c.score.weighted_components)
            )
            stage_counts["diversity"] = {
                "input": diversity_input,
                "output": len(ranked_candidates),
            }
            log_feature_end(
                "xalgo_diversity",
                duration_sec=stage_timings["diversity"],
                extra_detail=f"out={len(ranked_candidates)} adjusted={diversity_adjusted}",
            )

            stats["processed_count"] = len(ranked_candidates)

            # 5. Selection: 최종 상위 결과물 선정
            t0 = time.monotonic()
            log_feature_start("xalgo_selection", f"in={len(ranked_candidates)} top_k={top_k}")
            selected_candidates = self.selector.select(ranked_candidates, top_k=top_k)
            stage_timings["selection"] = round(time.monotonic() - t0, 3)
            stage_counts["selection"] = {
                "input": len(ranked_candidates),
                "output": len(selected_candidates),
            }
            top_preview = ",".join(
                [
                    f"{c.id}:{float(c.score.final_score):.3f}"
                    for c in selected_candidates[: min(3, len(selected_candidates))]
                ]
            )
            log_feature_end(
                "xalgo_selection",
                duration_sec=stage_timings["selection"],
                extra_detail=f"out={len(selected_candidates)} top={top_preview}",
            )
        except Exception as e:
            # 여기서 예외를 삼키지는 않는다. 상위에서 pipeline 실패를 감지해야 한다.
            log_feature_fail("pipeline_orchestrator_run", str(e))
            raise

        # ── 성능 메트릭 집계 ──────────────────────────────
        total_duration = round(time.monotonic() - pipeline_start, 3)
        total_filtered = (
            stage_counts.get("pre_filter", {}).get("filtered", 0)
            + stage_counts.get("post_filter", {}).get("filtered", 0)
        )
        # filtering_rate는 "필터 단계에서 제거된 비율"로 정의한다.
        # 과거 프론트/문서와의 호환을 위해 키는 유지하되, 의미 혼동을 막기 위해
        # removed_rate(동일 값)도 함께 제공한다.
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

        after_filter_count = len(ranked_candidates)
        selected_count = len(selected_candidates)
        original_count = int(stats.get("original_count") or 0)
        removed_count = int(total_filtered or 0)

        # API/대시보드에서 "왜 20→5인데 filtering_rate=0%"처럼 보이는지" 혼동을 줄이기 위해
        # 의미가 명확한 보조 지표를 함께 노출한다.
        stats["removed_count"] = removed_count
        stats["after_filter_count"] = after_filter_count
        stats["selected_count"] = selected_count
        stats["removed_rate"] = filtering_rate

        # 용어 정리:
        # - removed_count: pre/post filter 단계에서 "제거"된 건수
        # - after_filter_count: 필터 이후 남은 건수(=scoring 입력/출력 건수)
        # - selection_rate: top_k 선정 비율 (원본 대비 / 필터 후 대비)
        selection_rate_of_original = (
            (selected_count / original_count * 100.0) if original_count > 0 else 0.0
        )
        selection_rate_of_filtered = (
            (selected_count / after_filter_count * 100.0) if after_filter_count > 0 else 0.0
        )
        reduction_rate_of_original = (
            (1.0 - (selected_count / original_count)) * 100.0 if original_count > 0 else 0.0
        )

        stats["selection_rate_of_original"] = round(selection_rate_of_original / 100.0, 4)
        stats["selection_rate_of_filtered"] = round(selection_rate_of_filtered / 100.0, 4)
        stats["reduction_rate_of_original"] = round(reduction_rate_of_original / 100.0, 4)

        logger.info(
            "파이프라인 완료: original=%d → after_filter=%d (removed=%d, removed_rate=%.1f%%) → selected=%d "
            "(selection_rate=%.1f%% of original, %.1f%% of filtered, reduction=%.1f%% of original) (%.1f초)",
            original_count,
            after_filter_count,
            removed_count,
            filtering_rate * 100.0,
            selected_count,
            selection_rate_of_original,
            selection_rate_of_filtered,
            reduction_rate_of_original,
            total_duration,
            extra={
                "stage_timings": stage_timings,
                "total_duration": total_duration,
            },
        )

        log_feature_end(
            "pipeline_orchestrator_run",
            duration_sec=total_duration,
            extra_detail=(
                f"original={original_count} "
                f"after_filter={after_filter_count} "
                f"removed={removed_count} "
                f"selected={selected_count}"
            ),
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
