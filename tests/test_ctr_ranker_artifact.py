from services.ctr_ranker_artifact import CTRRankerArtifact


def test_artifact_score_from_features_standardizes_and_scores():
    artifact = CTRRankerArtifact(
        version="v1",
        created_at_iso="2026-02-09T00:00:00+09:00",
        feature_names=["a", "b"],
        scaler_mean=[10.0, 0.0],
        scaler_std=[2.0, 1.0],
        weights=[1.5, -2.0],
        intercept=0.25,
        training_meta={},
    )

    # z_a = (12-10)/2=1, z_b=(3-0)/1=3
    # score = 0.25 + 1.5*1 + (-2)*3 = 0.25 + 1.5 - 6 = -4.25
    s = artifact.score_from_features({"a": 12.0, "b": 3.0})
    assert abs(s - (-4.25)) < 1e-9


def test_artifact_score_from_features_missing_feature_defaults_to_zero():
    artifact = CTRRankerArtifact(
        version="v1",
        created_at_iso="2026-02-09T00:00:00+09:00",
        feature_names=["a"],
        scaler_mean=[0.0],
        scaler_std=[1.0],
        weights=[1.0],
        intercept=0.0,
        training_meta={},
    )
    assert artifact.score_from_features({}) == 0.0

