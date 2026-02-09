from __future__ import annotations

from pathlib import Path

from services.ctr_ranker_table import write_html


def test_write_html_includes_svg_charts(tmp_path: Path) -> None:
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
                "top5_before": [
                    {"title": "A", "score": 10.0, "proxy_score": 0.2},
                    {"title": "B", "score": 9.0, "proxy_score": 0.1},
                ],
                "top5_after": [
                    {"title": "B", "score": 0.9, "proxy_score": 0.1},
                    {"title": "A", "score": 0.8, "proxy_score": 0.2},
                ],
            }
        ],
    }

    out = tmp_path / "out.html"
    write_html(report, out)
    html_text = out.read_text(encoding="utf-8")

    # summary chart + rank shift chart
    assert 'data-chart="summary"' in html_text
    assert 'data-chart="rank-shift"' in html_text
    assert "<svg" in html_text

