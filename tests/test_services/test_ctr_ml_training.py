from pathlib import Path

import pytest


def test_ctr_ml_train_save_load_predict(tmp_path: Path):
    """아주 작은 synthetic feature로 학습/저장/로드/예측이 되는지 확인."""

    # NOTE: 실제 서비스의 extract_features(flatten) 결과와 동일하게 dict[str, float] 형태를 가정
    feature_rows = [
        {"title_length": 10.0, "hook_strength": 20.0, "total_score": 30.0},
        {"title_length": 20.0, "hook_strength": 10.0, "total_score": 40.0},
        {"title_length": 30.0, "hook_strength": 40.0, "total_score": 80.0},
        {"title_length": 40.0, "hook_strength": 30.0, "total_score": 90.0},
    ]
    labels = [0, 0, 1, 1]
    groups = ["r1", "r1", "r2", "r2"]

    from services.ctr_ml_training import load_ctr_ml_artifact, train_and_save

    out = train_and_save(
        feature_rows=feature_rows,
        labels=labels,
        groups=groups,
        out_dir=tmp_path,
        report_basename="synthetic",
    )

    model_path = Path(out["model_path"])
    report_json_path = Path(out["report_json_path"])
    report_md_path = Path(out["report_md_path"])

    assert model_path.exists()
    assert report_json_path.exists()
    assert report_md_path.exists()

    report = out["report"]
    assert "precision" in report
    assert "recall" in report
    assert "f1" in report
    assert "roc_auc" in report

    artifact = load_ctr_ml_artifact(model_path)
    prob = artifact.predict_proba({"title_length": 25.0, "hook_strength": 35.0, "total_score": 70.0})
    assert 0.0 <= prob <= 1.0


def test_ctr_predictor_adds_ml_fields_when_model_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """CTR_MODEL_PATH가 있으면 CTRPredictor 결과에 ML 예측값이 채워지고, 없으면 None 유지."""

    from services.ctr_ml_training import train_and_save
    from services.ctr_predictor import CTRPredictor

    out = train_and_save(
        feature_rows=[
            {"title_length": 10.0, "hook_strength": 20.0, "total_score": 30.0},
            {"title_length": 30.0, "hook_strength": 40.0, "total_score": 80.0},
        ],
        labels=[0, 1],
        groups=["r1", "r2"],
        out_dir=tmp_path,
        report_basename="synthetic2",
    )

    monkeypatch.setenv("CTR_MODEL_PATH", out["model_path"])
    predictor = CTRPredictor(gemini_client=None)
    result = predictor.predict_ctr(title="테스트 제목")
    assert result["ml_probability"] is not None
    assert result["ml_predicted_ctr"] is not None
    assert result["ml_prob"] == result["ml_probability"]

    # 개발/로컬 환경에 기존 CTR_MODEL_PATH가 설정돼 있어도 테스트가 안정적으로 동작하도록
    # "없는 상태"를 빈 문자열로 강제한다.
    monkeypatch.setenv("CTR_MODEL_PATH", "")
    predictor2 = CTRPredictor(gemini_client=None)
    result2 = predictor2.predict_ctr(title="테스트 제목")
    # API 호환성: 키는 존재하되, 모델이 없으면 None 이어야 한다.
    assert "ml_prob" in result2
    assert "ml_predicted_ctr" in result2
    assert "ml_probability" in result2
    assert result2["ml_prob"] is None
    assert result2["ml_predicted_ctr"] is None
    assert result2["ml_probability"] is None
