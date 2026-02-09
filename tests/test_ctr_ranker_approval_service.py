from __future__ import annotations

import pytest

from src.services.ctr_ranker_approval_service import (
    build_candidate_rows_from_raw_and_topk,
)


def test_build_candidate_rows_joins_raw_and_topk() -> None:
    raw_dataset = {
        "rows": [
            {
                "group_id": "벅스델타::0",
                "query": "벅스델타",
                "video": {
                    "id": "vid-1",
                    "title": "A",
                    "thumbnail": "https://i.ytimg.com/vi/vid-1/mqdefault.jpg",
                },
                "details": {"id": "vid-1"},
                "proxy_score": 0.5,
            }
        ]
    }

    topk_csv_text = "\n".join(
        [
            "group_id,variant,rank,score,proxy_score,title",
            "벅스델타,before,1,75.47,0.50,A",
            "벅스델타,after,1,0.87,0.51,A",
        ]
    )

    rows = build_candidate_rows_from_raw_and_topk(
        product_name="벅스델타",
        raw_dataset=raw_dataset,
        topk_csv_text=topk_csv_text,
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["title"] == "A"
    assert row["video_id"] == "vid-1"
    assert row["thumbnail_url"].startswith("https://")
    assert row["baseline_rank"] == 1
    assert row["after_rank"] == 1


def test_build_candidate_rows_requires_after_variant() -> None:
    raw_dataset = {"rows": []}
    topk_csv_text = "group_id,variant,rank,score,proxy_score,title\n"
    with pytest.raises(ValueError):
        build_candidate_rows_from_raw_and_topk(
            product_name="벅스델타",
            raw_dataset=raw_dataset,
            topk_csv_text=topk_csv_text,
        )
