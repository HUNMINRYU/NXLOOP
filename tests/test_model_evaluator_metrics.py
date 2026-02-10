"""
ModelEvaluator 평가 메트릭 테스트
"""


import pytest

from services.model_evaluator import ModelEvaluator


@pytest.fixture
def evaluator():
    return ModelEvaluator(output_dir="outputs/test_evaluations")


class TestRegressionMetrics:
    """회귀 메트릭 테스트"""

    def test_mae_perfect_predictions(self, evaluator):
        """완벽한 예측 시 MAE = 0"""
        actuals = [1.0, 2.0, 3.0, 4.0, 5.0]
        predictions = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert evaluator.calculate_mae(predictions, actuals) == 0.0

    def test_mae_with_error(self, evaluator):
        """오차가 있는 예측의 MAE"""
        actuals = [1.0, 2.0, 3.0]
        predictions = [1.5, 2.5, 3.5]
        assert evaluator.calculate_mae(predictions, actuals) == pytest.approx(0.5)

    def test_rmse_perfect(self, evaluator):
        """완벽한 예측 시 RMSE = 0"""
        actuals = [1.0, 2.0, 3.0]
        predictions = [1.0, 2.0, 3.0]
        assert evaluator.calculate_rmse(predictions, actuals) == 0.0

    def test_rmse_with_error(self, evaluator):
        """오차가 있는 예측의 RMSE"""
        actuals = [1.0, 2.0, 3.0]
        predictions = [2.0, 3.0, 4.0]
        # 각 오차 = 1, MSE = 1, RMSE = 1
        assert evaluator.calculate_rmse(predictions, actuals) == pytest.approx(1.0)

    def test_mape_calculation(self, evaluator):
        """MAPE 계산 검증"""
        actuals = [100.0, 200.0, 300.0]
        predictions = [110.0, 190.0, 310.0]
        # 오차율: 10%, 5%, 3.33% -> 평균 약 6.11%
        mape = evaluator.calculate_mape(predictions, actuals)
        assert 5.0 < mape < 7.0

    def test_mape_zero_actual(self, evaluator):
        """실제값이 0인 경우 해당 건 제외"""
        actuals = [0.0, 10.0, 20.0]
        predictions = [5.0, 12.0, 18.0]
        mape = evaluator.calculate_mape(predictions, actuals)
        assert mape != float("inf")

    def test_r_squared_perfect(self, evaluator):
        """완벽한 예측 시 R-squared = 1.0"""
        actuals = [1.0, 2.0, 3.0, 4.0]
        predictions = [1.0, 2.0, 3.0, 4.0]
        assert evaluator.calculate_r_squared(predictions, actuals) == pytest.approx(1.0)

    def test_r_squared_poor(self, evaluator):
        """나쁜 예측은 R-squared가 낮음"""
        actuals = [1.0, 2.0, 3.0, 4.0, 5.0]
        predictions = [5.0, 4.0, 3.0, 2.0, 1.0]  # 역순
        r2 = evaluator.calculate_r_squared(predictions, actuals)
        assert r2 < 0  # 평균보다 못한 예측

    def test_empty_inputs(self, evaluator):
        """빈 입력 처리"""
        assert evaluator.calculate_mae([], []) == float("inf")
        assert evaluator.calculate_rmse([], []) == float("inf")


class TestRankingMetrics:
    """순위 메트릭 테스트"""

    def test_ndcg_perfect_ranking(self, evaluator):
        """완벽한 순위 = NDCG 1.0"""
        ideal = ["a", "b", "c", "d", "e"]
        predicted = ["a", "b", "c", "d", "e"]
        ndcg = evaluator.calculate_ndcg(predicted, ideal)
        assert ndcg == pytest.approx(1.0)

    def test_ndcg_reversed_ranking(self, evaluator):
        """역순 순위 = NDCG < 1.0"""
        ideal = ["a", "b", "c", "d", "e"]
        predicted = ["e", "d", "c", "b", "a"]
        ndcg = evaluator.calculate_ndcg(predicted, ideal)
        assert 0.0 < ndcg < 1.0

    def test_ndcg_at_k(self, evaluator):
        """상위 K개에 대한 NDCG"""
        ideal = ["a", "b", "c", "d", "e"]
        predicted = ["a", "b", "e", "d", "c"]
        _ndcg_full = evaluator.calculate_ndcg(predicted, ideal)
        ndcg_k2 = evaluator.calculate_ndcg(predicted, ideal, k=2)
        # 상위 2개는 완벽 -> NDCG@2 = 1.0
        assert ndcg_k2 == pytest.approx(1.0)

    def test_ndcg_empty(self, evaluator):
        """빈 순위"""
        assert evaluator.calculate_ndcg([], ["a", "b"]) == 0.0

    def test_mrr_first_hit(self, evaluator):
        """첫 번째에서 정답 발견 시 MRR = 1.0"""
        rankings = [["correct", "b", "c"]]
        corrects = ["correct"]
        assert evaluator.calculate_mrr(rankings, corrects) == pytest.approx(1.0)

    def test_mrr_second_hit(self, evaluator):
        """두 번째에서 정답 발견 시 MRR = 0.5"""
        rankings = [["b", "correct", "c"]]
        corrects = ["correct"]
        assert evaluator.calculate_mrr(rankings, corrects) == pytest.approx(0.5)

    def test_mrr_not_found(self, evaluator):
        """정답을 찾지 못한 경우 MRR = 0.0"""
        rankings = [["a", "b", "c"]]
        corrects = ["d"]
        assert evaluator.calculate_mrr(rankings, corrects) == pytest.approx(0.0)


class TestEvaluatePredictions:
    """종합 평가 테스트"""

    def test_evaluate_returns_all_metrics(self, evaluator):
        """모든 메트릭이 반환되는지 확인"""
        preds = [5.0, 7.0, 9.0, 11.0]
        actuals = [4.5, 7.5, 8.5, 12.0]
        result = evaluator.evaluate_predictions(preds, actuals)

        assert "mae" in result
        assert "rmse" in result
        assert "mape" in result
        assert "r_squared" in result
        assert "sample_count" in result
        assert result["sample_count"] == 4


class TestCompareModels:
    """모델 비교 테스트"""

    def test_compare_identifies_winner(self, evaluator):
        """더 나은 모델을 정확히 식별"""
        actuals = [5.0, 10.0, 15.0, 20.0]
        model_a = [5.1, 9.9, 15.2, 19.8]  # 좋은 예측
        model_b = [7.0, 12.0, 13.0, 22.0]  # 나쁜 예측

        result = evaluator.compare_models(
            "model_a", model_a, "model_b", model_b, actuals
        )

        assert result["winner"] == "model_a"
        assert result["mae_improvement_pct"] > 0

    def test_compare_returns_both_metrics(self, evaluator):
        """두 모델의 메트릭이 모두 반환"""
        actuals = [1.0, 2.0, 3.0]
        result = evaluator.compare_models(
            "a", [1.1, 2.1, 3.1], "b", [1.5, 2.5, 3.5], actuals
        )

        assert "model_a" in result
        assert "model_b" in result
        assert "metrics" in result["model_a"]
        assert "metrics" in result["model_b"]
