from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from config.products import BLUEGUARD_PRODUCTS
from services.ctr_predictor import CTRPredictor
from services.ctr_ranker_report import build_youtube_dataset


class FakeYouTubeClient:
    def search(self, query: str, max_results: int = 3) -> list[dict[str, object]]:
        return [{"id": f"{query}-1", "title": f"{query} title"}]

    def get_video_details(self, video_id: str) -> dict[str, object] | None:
        # minimal fields used by _proxy_from_youtube_metrics
        return {
            "id": video_id,
            "published_at": "2026-02-01T00:00:00Z",
            "view_count": 1000,
            "like_count": 50,
            "comment_count": 10,
        }


def test_build_youtube_dataset_writes_raw_rows(tmp_path: Path) -> None:
    predictor = CTRPredictor(gemini_client=None)
    now = datetime(2026, 2, 9, 0, 0, 0, tzinfo=timezone.utc)
    raw_out = tmp_path / "raw.json"

    items = build_youtube_dataset(
        predictor=predictor,
        now=now,
        max_results_per_query=1,
        queries_per_product=1,
        yt_client=FakeYouTubeClient(),
        cache_dir=None,
        raw_out_path=raw_out,
    )

    assert items
    assert raw_out.exists()

    obj = json.loads(raw_out.read_text(encoding="utf-8"))
    assert obj["row_count"] >= 1
    assert isinstance(obj["rows"], list)


def test_build_youtube_dataset_filters_by_product_name(tmp_path: Path) -> None:
    predictor = CTRPredictor(gemini_client=None)
    now = datetime(2026, 2, 9, 0, 0, 0, tzinfo=timezone.utc)
    raw_out = tmp_path / "raw.json"

    # Use one real product name from config to validate filtering.
    product_name = str(BLUEGUARD_PRODUCTS[0]["name"])

    items = build_youtube_dataset(
        predictor=predictor,
        now=now,
        max_results_per_query=1,
        queries_per_product=1,
        product_names=[product_name],
        yt_client=FakeYouTubeClient(),
        cache_dir=None,
        raw_out_path=raw_out,
    )

    assert items
    assert all(it.group_id.startswith(f"{product_name}::") for it in items)


def test_build_youtube_dataset_raises_for_unknown_product_name() -> None:
    predictor = CTRPredictor(gemini_client=None)
    now = datetime(2026, 2, 9, 0, 0, 0, tzinfo=timezone.utc)

    try:
        build_youtube_dataset(
            predictor=predictor,
            now=now,
            max_results_per_query=1,
            queries_per_product=1,
            product_names=["존재하지않는제품"],
            yt_client=FakeYouTubeClient(),
            cache_dir=None,
            raw_out_path=None,
        )
        raise AssertionError("예외가 발생해야 합니다.")
    except ValueError as e:
        assert "product_names" in str(e)
