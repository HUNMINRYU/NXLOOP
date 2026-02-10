from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def flatten_ctr_features(features: dict[str, Any]) -> dict[str, float]:
    """CTRPredictor.extract_features() 결과를 학습용 피처(dict[str, float])로 평탄화한다.

    - breakdown의 각 점수는 그대로 피처로 사용
    - 집계 점수(rule/embedding/total)도 함께 포함
    """
    breakdown = features.get("breakdown") or {}
    if not isinstance(breakdown, dict):
        breakdown = {}

    flat: dict[str, float] = {}
    for k, v in breakdown.items():
        try:
            flat[str(k)] = float(v)
        except Exception:
            # 숫자 변환 불가인 경우 0으로 고정
            flat[str(k)] = 0.0

    for k in ["rule_tower_score", "embedding_tower_score", "total_score"]:
        try:
            flat[k] = float(features.get(k, 0.0))
        except Exception:
            flat[k] = 0.0

    return flat


def _ensure_sklearn() -> None:
    try:
        import sklearn  # noqa: F401
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "scikit-learn이 필요합니다. `pip install -e '.[dev]'` 또는 `uv sync`를 실행하세요."
        ) from e


@dataclass(frozen=True)
class CTRMLArtifact:
    cols: list[str]
    pipeline: Any

    def predict_proba(self, features: dict[str, float]) -> float:
        X = [[float(features.get(c, 0.0)) for c in self.cols]]
        prob = float(self.pipeline.predict_proba(X)[0][1])
        return max(0.0, min(1.0, prob))


def _train_pipeline(X: list[list[float]], y: list[int], seed: int) -> Any:
    _ensure_sklearn()
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    pipe = Pipeline(
        steps=[
            ("scaler", StandardScaler(with_mean=True, with_std=True)),
            (
                "clf",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    random_state=int(seed),
                ),
            ),
        ]
    )
    pipe.fit(X, y)
    return pipe


def train_and_save(
    *,
    feature_rows: list[dict[str, float]],
    labels: list[int],
    groups: list[str] | None,
    out_dir: Path,
    report_basename: str,
    n_splits: int = 5,
    seed: int = 42,
) -> dict[str, Any]:
    """extract_features(flatten) 결과로 분류 모델을 학습하고 리포트를 저장한다.

    반환(dict): 테스트/자동화에서 경로와 report를 바로 쓸 수 있도록 구성.
    """
    _ensure_sklearn()
    from sklearn.metrics import precision_recall_fscore_support, roc_auc_score
    from sklearn.model_selection import GroupKFold, StratifiedKFold

    if len(feature_rows) != len(labels):
        raise ValueError("feature_rows와 labels 길이가 일치해야 합니다.")
    if not feature_rows:
        raise ValueError("학습 데이터가 비어 있습니다.")

    cols = sorted({k for row in feature_rows for k in row.keys()})
    X = [[float(row.get(c, 0.0)) for c in cols] for row in feature_rows]
    y = [int(v) for v in labels]

    # CV는 "평가용"이라서, 데이터가 너무 작거나 그룹 분할로 단일 클래스가 되는 케이스는
    # 안전하게 스킵/대체한다. 최종 모델 학습은 전체 데이터로 진행한다.
    class_counts: dict[int, int] = {}
    for v in y:
        class_counts[v] = class_counts.get(v, 0) + 1
    min_class_count = min(class_counts.values()) if class_counts else 0

    def _has_two_classes(labels_: list[int]) -> bool:
        return len(set(labels_)) >= 2

    def _evaluate_fold(pipe: Any, X_test: list[list[float]], y_test: list[int]) -> tuple[float, float, float, float]:
        y_prob = pipe.predict_proba(X_test)[:, 1].tolist()
        y_pred = [1 if p >= 0.5 else 0 for p in y_prob]
        p, r, f1, _ = precision_recall_fscore_support(y_test, y_pred, average="binary", zero_division=0)
        try:
            auc = float(roc_auc_score(y_test, y_prob))
        except Exception:
            auc = 0.0
        return float(p), float(r), float(f1), float(auc)

    p_list: list[float] = []
    r_list: list[float] = []
    f1_list: list[float] = []
    auc_list: list[float] = []

    # 1) 그룹 기반 CV 시도 (가능한 경우)
    valid_folds = 0
    if groups and len(set(groups)) >= 2:
        n_groups = len(set(groups))
        n = min(int(n_splits), n_groups)
        splitter = GroupKFold(n_splits=max(2, n))
        for train_idx, test_idx in splitter.split(X, y, groups=groups):
            X_train = [X[i] for i in train_idx]
            y_train = [y[i] for i in train_idx]
            X_test = [X[i] for i in test_idx]
            y_test = [y[i] for i in test_idx]

            # 그룹 분할 특성상 train이 단일 클래스가 되기 쉬움 -> 해당 fold는 스킵
            if not _has_two_classes(y_train) or len(y_train) < 2:
                continue

            pipe = _train_pipeline(X_train, y_train, seed=seed)
            p, r, f1, auc = _evaluate_fold(pipe, X_test, y_test)
            p_list.append(p)
            r_list.append(r)
            f1_list.append(f1)
            auc_list.append(auc)
            valid_folds += 1

    # 2) 그룹 기반 CV가 유효하지 않으면 stratified CV로 대체(데이터가 충분할 때만)
    if valid_folds == 0 and min_class_count >= 2:
        n = min(int(n_splits), int(min_class_count))
        if n >= 2:
            splitter = StratifiedKFold(n_splits=int(n), shuffle=True, random_state=int(seed))
            for train_idx, test_idx in splitter.split(X, y):
                X_train = [X[i] for i in train_idx]
                y_train = [y[i] for i in train_idx]
                X_test = [X[i] for i in test_idx]
                y_test = [y[i] for i in test_idx]

                if not _has_two_classes(y_train) or len(y_train) < 2:
                    continue

                pipe = _train_pipeline(X_train, y_train, seed=seed)
                p, r, f1, auc = _evaluate_fold(pipe, X_test, y_test)
                p_list.append(p)
                r_list.append(r)
                f1_list.append(f1)
                auc_list.append(auc)
                valid_folds += 1

    # 최종 모델은 전체 데이터로 학습
    final_pipe = _train_pipeline(X, y, seed=seed)
    artifact = CTRMLArtifact(cols=cols, pipeline=final_pipe)

    report = {
        "n_samples": int(len(y)),
        "n_features": int(len(cols)),
        "precision": float(sum(p_list) / len(p_list)) if p_list else 0.0,
        "recall": float(sum(r_list) / len(r_list)) if r_list else 0.0,
        "f1": float(sum(f1_list) / len(f1_list)) if f1_list else 0.0,
        "roc_auc": float(sum(auc_list) / len(auc_list)) if auc_list else 0.0,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = out_dir / f"{report_basename}.joblib"
    report_json_path = out_dir / f"{report_basename}.report.json"
    report_md_path = out_dir / f"{report_basename}.report.md"

    import joblib

    joblib.dump({"cols": artifact.cols, "pipeline": artifact.pipeline}, model_path)
    report_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md_path.write_text(
        "\n".join(
            [
                f"# CTR ML Training Report: {report_basename}",
                "",
                f"- n_samples: {report['n_samples']}",
                f"- n_features: {report['n_features']}",
                f"- precision: {report['precision']:.4f}",
                f"- recall: {report['recall']:.4f}",
                f"- f1: {report['f1']:.4f}",
                f"- roc_auc: {report['roc_auc']:.4f}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return {
        "model_path": str(model_path),
        "report_json_path": str(report_json_path),
        "report_md_path": str(report_md_path),
        "report": report,
    }


def load_ctr_ml_artifact(path: str | Path) -> CTRMLArtifact:
    _ensure_sklearn()
    import joblib

    obj = joblib.load(Path(path))
    if not isinstance(obj, dict):
        raise ValueError("모델 아티팩트 형식이 올바르지 않습니다.")
    cols = obj.get("cols")
    pipe = obj.get("pipeline")
    if not isinstance(cols, list) or pipe is None:
        raise ValueError("모델 아티팩트에 cols/pipeline이 없습니다.")
    return CTRMLArtifact(cols=[str(c) for c in cols], pipeline=pipe)
