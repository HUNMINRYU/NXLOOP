import numpy as np

from services.ctr_ranker_training import train_linear_ridge_ranker


def test_train_linear_ridge_ranker_produces_artifact_with_expected_shapes():
    feature_names = ["f1", "f2", "f3"]
    x = np.array(
        [
            [1.0, 0.0, 2.0],
            [2.0, 1.0, 0.0],
            [0.0, 1.0, 1.0],
            [3.0, 2.0, 1.0],
        ],
        dtype=float,
    )
    y = np.array([0.1, 0.2, 0.0, 0.4], dtype=float)

    artifact = train_linear_ridge_ranker(
        feature_names=feature_names,
        x=x,
        y=y,
        alpha=1.0,
        training_meta={"mode": "unit-test"},
    )

    assert artifact.feature_names == feature_names
    assert len(artifact.weights) == len(feature_names)
    assert len(artifact.scaler_mean) == len(feature_names)
    assert len(artifact.scaler_std) == len(feature_names)
