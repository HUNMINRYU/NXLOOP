from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.ctr_ranker_report import load_youtube_raw_dataset


def test_load_youtube_raw_dataset_filters_by_product_name(tmp_path: Path) -> None:
    raw = tmp_path / "raw.json"
    raw.write_text(
        json.dumps(
            {
                "generated_at_iso": "2026-02-09T00:00:00+00:00",
                "row_count": 2,
                "rows": [
                    {
                        "group_id": "벅스델타::0",
                        "query": "벅스델타",
                        "video": {"id": "v1", "title": "t1"},
                        "details": {"view_count": 1},
                        "proxy_score": 0.1,
                    },
                    {
                        "group_id": "파리싹::0",
                        "query": "파리싹",
                        "video": {"id": "v2", "title": "t2"},
                        "details": {"view_count": 2},
                        "proxy_score": 0.2,
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    items = load_youtube_raw_dataset(raw_path=raw, product_names=["벅스델타"])
    assert len(items) == 1
    assert items[0].group_id == "벅스델타::0"
    assert items[0].title == "t1"
    assert items[0].item_id.startswith("v1:")


def test_load_youtube_raw_dataset_raises_when_product_not_found(tmp_path: Path) -> None:
    raw = tmp_path / "raw.json"
    raw.write_text(
        json.dumps(
            {
                "generated_at_iso": "2026-02-09T00:00:00+00:00",
                "row_count": 1,
                "rows": [
                    {
                        "group_id": "파리싹::0",
                        "query": "파리싹",
                        "video": {"id": "v2", "title": "t2"},
                        "details": {"view_count": 2},
                        "proxy_score": 0.2,
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_youtube_raw_dataset(raw_path=raw, product_names=["벅스델타"])

