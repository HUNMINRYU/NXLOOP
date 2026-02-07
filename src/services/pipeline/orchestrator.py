from __future__ import annotations
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
        pipeline_context: dict[str, Any] = None
    ) -> dict[str, Any]:
        """X 알고리즘 기반 파이프라인 전체 실행"""
        stats: dict[str, Any] = {}
        context = pipeline_context or {}

        # 1. Source: Raw Data -> Candidate 변환 (비동기 처리 최적화)
        candidates = await self.source.item_to_candidate(raw_data, brand_context=context.get("brand_guidelines", ""))
        stats["original_count"] = len(candidates)

        # 2. Filter & Hydrate (Candidate 생성 및 정보 보강)
        candidates = self._safe_stage("pre_filter", self.filter.filter, candidates)
        
        candidates = await self._safe_async_stage(
            "hydration", self.hydrator.hydrate, candidates
        )

        candidates = self._safe_stage("post_filter", self.filter.filter, candidates)
        stats["hydrated_count"] = len(candidates)
        
        if not candidates:
            return {"insights": [], "stats": stats, "summary": "분석 가능한 데이터가 없습니다."}

        # 3. AI Behavioral Scoring (X's Grok-style Multi-Objective Scoring)
        ranked_candidates = await self._safe_async_stage(
            "scoring", 
            lambda cands: self.scorer.score(cands, context), 
            candidates
        )

        # 4. Multi-Factor Diversity (Categorical & Semantic Diversity)
        history_context = context.get("history", {})
        ranked_candidates = self._safe_stage(
            "diversity", 
            lambda cands: self.diversity_scorer.apply(cands, history_context), 
            ranked_candidates
        )

        stats["processed_count"] = len(ranked_candidates)

        # 5. Selection: 최종 상위 결과물 선정
        top_k = context.get("top_k", 5)
        selected_candidates = self.selector.select(ranked_candidates, top_k=top_k)

        # AI 요약 생성 (X 알고리즘 통합 인사이트)
        total_reasoning = " ".join(
            [
                c.metadata.get("ai_reasoning", "")
                for c in selected_candidates
                if c.metadata.get("ai_reasoning")
            ]
        )
        summary = total_reasoning[:500] if total_reasoning else "X 알고리즘 기반 고효율 후보군 선별 완료."

        # Side effects 발송
        self.side_effects.emit(
            "pipeline_completed",
            stats=stats,
            result_count=len(selected_candidates),
        )

        return {
            "insights": self.selector.format_for_response(selected_candidates),
            "stats": stats,
            "summary": summary
        }

    # --- 유틸리티 메서드 ---
    def _safe_stage(self, stage_name: str, fn: Any, candidates: list[Candidate]) -> list[Candidate]:
        backup = list(candidates)
        try:
            return fn(candidates)
        except Exception as e:
            logger.error(f"{stage_name} 실패, backup 사용: {e}")
            self.side_effects.emit("stage_error", stage=stage_name, error=str(e))
            return backup

    async def _safe_async_stage(self, stage_name: str, fn: Any, candidates: list[Candidate]) -> list[Candidate]:
        backup = list(candidates)
        try:
            return await fn(candidates)
        except Exception as e:
            logger.error(f"{stage_name} 실패, backup 사용: {e}")
            self.side_effects.emit("stage_error", stage=stage_name, error=str(e))
            return backup
