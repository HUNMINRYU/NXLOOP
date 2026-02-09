from __future__ import annotations

from pathlib import Path

from services.ctr_ranker_charts import write_pdf


def test_write_pdf_creates_non_empty_file(tmp_path: Path) -> None:
    report = {
        "k": 5,
        "ndcg_before": 0.9,
        "ndcg_after": 1.0,
        "spearman_before": 0.5,
        "spearman_after": 0.8,
        "top1_before": 0.0,
        "top1_after": 1.0,
        "groups": [
            {
                "group_id": "G1",
                "top5_before": [{"title": "A"}, {"title": "B"}],
                "top5_after": [{"title": "B"}, {"title": "A"}],
            }
        ],
    }

    out = tmp_path / "out.pdf"
    write_pdf(report, out)

    assert out.exists()
    assert out.stat().st_size > 1000

