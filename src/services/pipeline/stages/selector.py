from typing import Any

from services.pipeline.types import Candidate

# -------------------------------------------------------------------------


class TopInsightSelector:
    """최종 결과 선정 및 포맷팅 (Selection Layer)"""

    def select(
        self, ranked_candidates: list[Candidate], top_k: int = 3
    ) -> list[Candidate]:
        # 상위 K개 선정
        selected = ranked_candidates[:top_k]

        for rank, cand in enumerate(selected, 1):
            cand.is_selected = True
            cand.selection_reason = f"Rank {rank}: {cand.score.explanation}"
            cand.metadata["rank"] = rank

        return selected

    def format_for_response(self, selected: list[Candidate]) -> list[dict[str, Any]]:
        """UI/API 응답에 쓰기 좋은 dict 형태로 변환."""
        results: list[dict[str, Any]] = []
        for cand in selected:
            rank = int(cand.metadata.get("rank", 0) or 0)
            results.append(
                {
                    "rank": rank,
                    "author": cand.author.username,
                    "content": cand.content,
                    "score": cand.score.final_score,
                    "reason": cand.score.explanation,
                    "features": {
                        "purchase": cand.features.purchase_intent,
                        "viral": cand.features.reply_inducing,
                    },
                }
            )
        return results
