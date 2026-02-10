"""
모델 평가 및 로깅

평가 메트릭:
- 회귀: MAE, RMSE, MAPE, R-squared
- 순위: NDCG@K, MRR (Mean Reciprocal Rank)
- 모델 비교: 메트릭 기반 통계 비교
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any


class ModelEvaluator:
    """모델 성능 평가 및 추적"""

    def __init__(self, output_dir: str = "outputs/evaluations") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ── 예측 로깅 ─────────────────────────────────────────

    def log_prediction(
        self,
        model_name: str,
        input_data: dict,
        output: dict,
        ground_truth: dict | None = None,
    ) -> None:
        """예측 결과를 JSONL 파일에 기록"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "model": model_name,
            "input": input_data,
            "output": output,
            "ground_truth": ground_truth,
        }
        log_file = (
            self.output_dir
            / f"{model_name}_{datetime.now().strftime('%Y%m%d')}.jsonl"
        )
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    # ── 회귀 메트릭 ───────────────────────────────────────

    @staticmethod
    def calculate_mae(predictions: list[float], actuals: list[float]) -> float:
        """Mean Absolute Error (평균 절대 오차)"""
        if not predictions or len(predictions) != len(actuals):
            return float("inf")
        return sum(abs(p - a) for p, a in zip(predictions, actuals, strict=True)) / len(predictions)

    @staticmethod
    def calculate_rmse(predictions: list[float], actuals: list[float]) -> float:
        """Root Mean Squared Error (제곱근 평균 제곱 오차)"""
        if not predictions or len(predictions) != len(actuals):
            return float("inf")
        mse = sum((p - a) ** 2 for p, a in zip(predictions, actuals, strict=True)) / len(predictions)
        return math.sqrt(mse)

    @staticmethod
    def calculate_mape(predictions: list[float], actuals: list[float]) -> float:
        """Mean Absolute Percentage Error (평균 절대 백분율 오차)"""
        if not predictions or len(predictions) != len(actuals):
            return float("inf")
        valid_pairs = [(p, a) for p, a in zip(predictions, actuals, strict=True) if a != 0]
        if not valid_pairs:
            return float("inf")
        return (
            sum(abs((a - p) / a) for p, a in valid_pairs) / len(valid_pairs) * 100
        )

    @staticmethod
    def calculate_r_squared(predictions: list[float], actuals: list[float]) -> float:
        """R-squared (결정 계수)"""
        if not predictions or len(predictions) != len(actuals):
            return 0.0
        n = len(actuals)
        mean_actual = sum(actuals) / n
        ss_tot = sum((a - mean_actual) ** 2 for a in actuals)
        ss_res = sum((a - p) ** 2 for p, a in zip(predictions, actuals, strict=True))
        if ss_tot == 0:
            return 1.0 if ss_res == 0 else 0.0
        return 1 - (ss_res / ss_tot)

    # ── 순위 메트릭 ───────────────────────────────────────

    @staticmethod
    def calculate_ndcg(
        predicted_ranking: list[str],
        ideal_ranking: list[str],
        k: int | None = None,
    ) -> float:
        """
        Normalized Discounted Cumulative Gain (NDCG@K)

        Args:
            predicted_ranking: 예측된 순위 (아이템 ID 리스트)
            ideal_ranking: 이상적인 순위 (아이템 ID 리스트)
            k: 상위 K개까지만 평가 (None이면 전체)
        """
        if not predicted_ranking or not ideal_ranking:
            return 0.0

        # 이상적인 순위에서의 관련도 점수 (순위 역순으로 부여)
        relevance: dict[str, float] = {}
        for rank, item_id in enumerate(ideal_ranking):
            relevance[item_id] = max(0, len(ideal_ranking) - rank)

        if k is not None:
            predicted_ranking = predicted_ranking[:k]
            ideal_top = ideal_ranking[:k]
        else:
            ideal_top = ideal_ranking

        # DCG 계산
        dcg = 0.0
        for rank, item_id in enumerate(predicted_ranking):
            rel = relevance.get(item_id, 0.0)
            dcg += rel / math.log2(rank + 2)  # rank+2 (1-indexed + log2 보정)

        # IDCG 계산 (이상적 순서)
        idcg = 0.0
        ideal_rels = sorted(
            [relevance.get(item_id, 0.0) for item_id in ideal_top],
            reverse=True,
        )
        for rank, rel in enumerate(ideal_rels):
            idcg += rel / math.log2(rank + 2)

        if idcg == 0:
            return 0.0
        return dcg / idcg

    @staticmethod
    def calculate_mrr(
        predicted_rankings: list[list[str]],
        correct_items: list[str],
    ) -> float:
        """
        Mean Reciprocal Rank (MRR)

        Args:
            predicted_rankings: 각 쿼리별 예측 순위 리스트
            correct_items: 각 쿼리별 정답 아이템
        """
        if not predicted_rankings or len(predicted_rankings) != len(correct_items):
            return 0.0

        reciprocal_ranks = []
        for ranking, correct in zip(
            predicted_rankings, correct_items, strict=True
        ):
            if correct in ranking:
                rank = ranking.index(correct) + 1
                reciprocal_ranks.append(1.0 / rank)
            else:
                reciprocal_ranks.append(0.0)

        return sum(reciprocal_ranks) / len(reciprocal_ranks)

    # ── 종합 평가 ─────────────────────────────────────────

    def evaluate_predictions(
        self,
        predictions: list[float],
        actuals: list[float],
    ) -> dict[str, float]:
        """
        예측값과 실제값을 비교하여 전체 회귀 메트릭을 계산한다.

        Returns:
            {mae, rmse, mape, r_squared, sample_count}
        """
        return {
            "mae": round(self.calculate_mae(predictions, actuals), 4),
            "rmse": round(self.calculate_rmse(predictions, actuals), 4),
            "mape": round(self.calculate_mape(predictions, actuals), 2),
            "r_squared": round(self.calculate_r_squared(predictions, actuals), 4),
            "sample_count": len(predictions),
        }

    def evaluate_ranking(
        self,
        predicted_ranking: list[str],
        ideal_ranking: list[str],
        k: int = 5,
    ) -> dict[str, float]:
        """
        순위 예측 품질을 평가한다.

        Returns:
            {ndcg_at_k, k}
        """
        return {
            "ndcg_at_k": round(self.calculate_ndcg(predicted_ranking, ideal_ranking, k), 4),
            "k": k,
        }

    # ── 모델 비교 ─────────────────────────────────────────

    def compare_models(
        self,
        model_a_name: str,
        model_a_predictions: list[float],
        model_b_name: str,
        model_b_predictions: list[float],
        actuals: list[float],
    ) -> dict[str, Any]:
        """
        두 모델의 성능을 비교한다.

        Returns:
            두 모델의 메트릭과 승자 정보
        """
        metrics_a = self.evaluate_predictions(model_a_predictions, actuals)
        metrics_b = self.evaluate_predictions(model_b_predictions, actuals)

        # 낮은 MAE가 더 좋음
        winner = model_a_name if metrics_a["mae"] < metrics_b["mae"] else model_b_name
        improvement_pct = 0.0
        if metrics_b["mae"] > 0:
            improvement_pct = (
                (metrics_b["mae"] - metrics_a["mae"]) / metrics_b["mae"] * 100
            )

        return {
            "model_a": {"name": model_a_name, "metrics": metrics_a},
            "model_b": {"name": model_b_name, "metrics": metrics_b},
            "winner": winner,
            "mae_improvement_pct": round(improvement_pct, 2),
        }

    # ── 보고서 생성 ───────────────────────────────────────

    def generate_report(self) -> str:
        """모델 평가 보고서 생성"""
        report_lines = [
            "# 모델 평가 보고서",
            f"생성 시각: {datetime.now().isoformat()}",
            "",
        ]
        for log_file in self.output_dir.glob("*.jsonl"):
            count = sum(1 for _ in log_file.open(encoding="utf-8"))
            report_lines.append(f"- {log_file.stem}: {count}건")

        report_lines.append("")
        report_lines.append("## 사용 가능 메트릭")
        report_lines.append("- 회귀: MAE, RMSE, MAPE, R-squared")
        report_lines.append("- 순위: NDCG@K, MRR")

        return "\n".join(report_lines)
