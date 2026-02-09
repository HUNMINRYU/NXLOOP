from __future__ import annotations

import argparse
import csv
import html
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

KST = timezone(timedelta(hours=9))


@dataclass(frozen=True)
class ReportPaths:
    report_json: Path
    out_html: Path
    out_summary_csv: Path
    out_top5_csv: Path


def _kst_date_str(now_utc: datetime | None = None) -> str:
    now = now_utc or datetime.now(timezone.utc)
    return now.astimezone(KST).strftime("%Y-%m-%d")


def default_paths(*, date_str: str) -> ReportPaths:
    report_json = Path(f"outputs/ctr_ranker/reports/{date_str}-before-after.json")
    out_html = Path(f"docs/{date_str}/codex/ctr-ranker-before-after.html")
    out_summary_csv = Path(f"outputs/ctr_ranker/reports/{date_str}-summary.csv")
    out_top5_csv = Path(f"outputs/ctr_ranker/reports/{date_str}-top5.csv")
    return ReportPaths(
        report_json=report_json,
        out_html=out_html,
        out_summary_csv=out_summary_csv,
        out_top5_csv=out_top5_csv,
    )


def load_report(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("report JSON 최상위는 object(dict)여야 합니다.")
    return data


def _fmt(x: Any, *, digits: int = 4) -> str:
    try:
        f = float(x)
    except (TypeError, ValueError):
        return str(x)
    return f"{f:.{digits}f}"


def _render_table(rows: list[list[str]]) -> str:
    """
    추가 의존성 없이 터미널에 보기 좋은 단순 표를 만든다.
    """
    if not rows:
        return ""
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]

    def fmt_row(r: list[str]) -> str:
        parts = [r[i].ljust(widths[i]) for i in range(len(r))]
        return " | ".join(parts)

    header = fmt_row(rows[0])
    sep = "-+-".join("-" * w for w in widths)
    body = "\n".join(fmt_row(r) for r in rows[1:])
    return "\n".join([header, sep, body])


def print_report_tables(report: dict[str, Any], *, max_groups: int = 3) -> None:
    k = int(report.get("k", 5))

    summary = [
        ["Metric", "Before", "After"],
        [f"NDCG@{k}", _fmt(report.get("ndcg_before")), _fmt(report.get("ndcg_after"))],
        ["Spearman", _fmt(report.get("spearman_before")), _fmt(report.get("spearman_after"))],
        ["Top-1 hit", _fmt(report.get("top1_before")), _fmt(report.get("top1_after"))],
    ]
    print(_render_table(summary))
    print("")

    groups = list(report.get("groups", []) or [])[: max(0, int(max_groups))]
    for g in groups:
        gid = str(g.get("group_id"))
        print(f"[Group] {gid}")
        print("")

        before_rows = [["rank", "score", "proxy_score", "title"]]
        for i, row in enumerate(g.get("top5_before", []) or [], start=1):
            before_rows.append(
                [
                    str(i),
                    _fmt(row.get("score")),
                    _fmt(row.get("proxy_score")),
                    str(row.get("title", "")),
                ]
            )
        print("Before (baseline)")
        print(_render_table(before_rows))
        print("")

        after_rows = [["rank", "score", "proxy_score", "title"]]
        for i, row in enumerate(g.get("top5_after", []) or [], start=1):
            after_rows.append(
                [
                    str(i),
                    _fmt(row.get("score")),
                    _fmt(row.get("proxy_score")),
                    str(row.get("title", "")),
                ]
            )
        print("After (ML)")
        print(_render_table(after_rows))
        print("")


def write_summary_csv(report: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    k = int(report.get("k", 5))
    rows: list[list[Any]] = [
        ["metric", "before", "after"],
        [f"ndcg@{k}", report.get("ndcg_before"), report.get("ndcg_after")],
        ["spearman", report.get("spearman_before"), report.get("spearman_after")],
        ["top1_hit", report.get("top1_before"), report.get("top1_after")],
    ]
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)


def _iter_top5_rows(
    report: dict[str, Any],
) -> Iterable[list[Any]]:
    yield ["group_id", "variant", "rank", "score", "proxy_score", "title"]
    for g in report.get("groups", []) or []:
        gid = str(g.get("group_id"))
        for variant_key, variant_name in (("top5_before", "before"), ("top5_after", "after")):
            for i, row in enumerate(g.get(variant_key, []) or [], start=1):
                yield [
                    gid,
                    variant_name,
                    i,
                    row.get("score"),
                    row.get("proxy_score"),
                    row.get("title", ""),
                ]


def write_top5_csv(report: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for r in _iter_top5_rows(report):
            writer.writerow(r)


def write_html(report: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    k = int(report.get("k", 5))

    def esc(s: Any) -> str:
        return html.escape(str(s))

    def _truncate(s: str, *, max_len: int = 48) -> str:
        s = (s or "").strip()
        if len(s) <= max_len:
            return s
        return s[: max(0, max_len - 1)] + "…"

    def _svg_summary_chart() -> str:
        before = {
            f"NDCG@{k}": float(report.get("ndcg_before") or 0.0),
            "Spearman": float(report.get("spearman_before") or 0.0),
            "Top-1 hit": float(report.get("top1_before") or 0.0),
        }
        after = {
            f"NDCG@{k}": float(report.get("ndcg_after") or 0.0),
            "Spearman": float(report.get("spearman_after") or 0.0),
            "Top-1 hit": float(report.get("top1_after") or 0.0),
        }

        labels = list(before.keys())
        max_val = max([1e-9, *before.values(), *after.values()])

        width = 760
        left_pad = 140
        top_pad = 34
        row_h = 38
        bar_w = width - left_pad - 24
        height = top_pad + row_h * len(labels) + 22

        parts: list[str] = []
        parts.append(f'<svg class="chart" data-chart="summary" viewBox="0 0 {width} {height}" role="img" aria-label="Before/After Summary Metrics">')
        parts.append('<text x="0" y="18" class="chart-title">Summary (Before vs After)</text>')
        parts.append(
            f'<rect x="{left_pad}" y="6" width="10" height="10" rx="2" fill="#94a3b8" /><text x="{left_pad + 16}" y="15" class="legend">Before</text>'
        )
        parts.append(
            f'<rect x="{left_pad + 90}" y="6" width="10" height="10" rx="2" fill="#0ea5e9" /><text x="{left_pad + 106}" y="15" class="legend">After</text>'
        )

        for i, label in enumerate(labels):
            y = top_pad + i * row_h
            b = before[label]
            a = after[label]
            bw = round((b / max_val) * bar_w)
            aw = round((a / max_val) * bar_w)

            parts.append(f'<text x="0" y="{y + 16}" class="axis-label">{esc(label)}</text>')
            # baseline bar
            parts.append(
                f'<rect x="{left_pad}" y="{y}" width="{bw}" height="12" rx="4" fill="#94a3b8" opacity="0.85"><title>{esc(label)} Before: {b:.4f}</title></rect>'
            )
            # after bar (stacked below)
            parts.append(
                f'<rect x="{left_pad}" y="{y + 16}" width="{aw}" height="12" rx="4" fill="#0ea5e9" opacity="0.90"><title>{esc(label)} After: {a:.4f}</title></rect>'
            )
            parts.append(
                f'<text x="{left_pad + bar_w + 6}" y="{y + 10}" class="value">{b:.4f}</text>'
            )
            parts.append(
                f'<text x="{left_pad + bar_w + 6}" y="{y + 26}" class="value">{a:.4f}</text>'
            )

        parts.append("</svg>")
        return "".join(parts)

    def _svg_rank_shift(group: dict[str, Any]) -> str:
        """
        Top-5(before/after)만으로 '순위 이동'을 간단히 시각화한다.
        - 양쪽 모두에 등장하는 title은 라인으로 연결
        - 한쪽에만 등장하면 점만 표시
        """
        before_list = list(group.get("top5_before", []) or [])
        after_list = list(group.get("top5_after", []) or [])

        before_rank: dict[str, int] = {str(r.get("title", "")): i for i, r in enumerate(before_list, start=1)}
        after_rank: dict[str, int] = {str(r.get("title", "")): i for i, r in enumerate(after_list, start=1)}

        titles: list[str] = []
        for t in list(before_rank.keys()) + list(after_rank.keys()):
            if t and t not in titles:
                titles.append(t)

        width = 760
        left_x = 180
        right_x = 620
        top_pad = 36
        row_h = 30
        height = top_pad + row_h * 5 + 40

        def y_for_rank(r: int) -> int:
            return top_pad + (max(1, min(5, int(r))) - 1) * row_h

        parts: list[str] = []
        parts.append(f'<svg class="chart" data-chart="rank-shift" viewBox="0 0 {width} {height}" role="img" aria-label="Rank shift chart">')
        parts.append('<text x="0" y="18" class="chart-title">Rank Shift (Top-5)</text>')
        parts.append(f'<text x="{left_x - 42}" y="18" class="legend">Before</text>')
        parts.append(f'<text x="{right_x - 32}" y="18" class="legend">After</text>')

        # grid lines (rank 1..5)
        for r in range(1, 6):
            y = y_for_rank(r)
            parts.append(f'<line x1="{left_x}" y1="{y}" x2="{right_x}" y2="{y}" stroke="#e5e7eb" stroke-width="1" />')
            parts.append(f'<text x="{left_x - 18}" y="{y + 4}" class="rank">{r}</text>')
            parts.append(f'<text x="{right_x + 10}" y="{y + 4}" class="rank">{r}</text>')

        # lines + nodes
        for t in titles:
            b = before_rank.get(t)
            a = after_rank.get(t)
            if b is None and a is None:
                continue

            color = "#0ea5e9" if (b is not None and a is not None) else "#94a3b8"
            if b is not None and a is not None:
                y0 = y_for_rank(b)
                y1 = y_for_rank(a)
                parts.append(
                    f'<line x1="{left_x}" y1="{y0}" x2="{right_x}" y2="{y1}" stroke="{color}" stroke-width="2" opacity="0.75"><title>{esc(t)}: {b} → {a}</title></line>'
                )

            if b is not None:
                y0 = y_for_rank(b)
                label = _truncate(t, max_len=52)
                parts.append(
                    f'<circle cx="{left_x}" cy="{y0}" r="5" fill="{color}" opacity="0.95"><title>{esc(t)} (Before #{b})</title></circle>'
                )
                parts.append(
                    f'<text x="{left_x - 10}" y="{y0 - 8}" text-anchor="end" class="item">{esc(label)}</text>'
                )

            if a is not None:
                y1 = y_for_rank(a)
                label = _truncate(t, max_len=52)
                parts.append(
                    f'<circle cx="{right_x}" cy="{y1}" r="5" fill="{color}" opacity="0.95"><title>{esc(t)} (After #{a})</title></circle>'
                )
                parts.append(
                    f'<text x="{right_x + 10}" y="{y1 - 8}" class="item">{esc(label)}</text>'
                )

        parts.append("</svg>")
        return "".join(parts)

    def tr(cells: list[str], *, th: bool = False) -> str:
        tag = "th" if th else "td"
        inner = "".join(f"<{tag}>{c}</{tag}>" for c in cells)
        return f"<tr>{inner}</tr>"

    summary_rows = [
        tr(["Metric", "Before", "After"], th=True),
        tr([f"NDCG@{k}", esc(_fmt(report.get("ndcg_before"))), esc(_fmt(report.get("ndcg_after")))]),
        tr(["Spearman", esc(_fmt(report.get("spearman_before"))), esc(_fmt(report.get("spearman_after")))]),
        tr(["Top-1 hit", esc(_fmt(report.get("top1_before"))), esc(_fmt(report.get("top1_after")))]),
    ]

    group_sections: list[str] = []
    for g in report.get("groups", []) or []:
        gid = esc(g.get("group_id"))

        def build_top_table(group: dict[str, Any], key: str) -> str:
            rows = [tr(["rank", "score", "proxy_score", "title"], th=True)]
            for i, row in enumerate(group.get(key, []) or [], start=1):
                rows.append(
                    tr(
                        [
                            esc(i),
                            esc(_fmt(row.get("score"))),
                            esc(_fmt(row.get("proxy_score"))),
                            esc(row.get("title", "")),
                        ]
                    )
                )
            return "<table>" + "".join(rows) + "</table>"

        group_sections.append(f"<h2>Group: {gid}</h2>")
        group_sections.append('<div class="charts">')
        group_sections.append(_svg_rank_shift(g))
        group_sections.append("</div>")
        group_sections.append("<h3>Before (baseline)</h3>")
        group_sections.append(build_top_table(g, "top5_before"))
        group_sections.append("<h3>After (ML)</h3>")
        group_sections.append(build_top_table(g, "top5_after"))

    html_doc = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>CTR Ranker Before/After</title>
  <style>
    :root {{
      --ink: #0f172a;
      --muted: #475569;
      --panel: #ffffff;
      --border: #e5e7eb;
      --bg: #f8fafc;
      --before: #94a3b8;
      --after: #0ea5e9;
    }}
    body {{
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
      margin: 0;
      padding: 24px;
      background: var(--bg);
      color: var(--ink);
    }}
    .wrap {{ max-width: 1040px; margin: 0 auto; }}
    h1 {{ margin: 0 0 8px; letter-spacing: -0.02em; }}
    h2 {{ margin-top: 28px; }}
    .sub {{ color: var(--muted); margin: 0 0 18px; }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
      box-shadow: 0 1px 0 rgba(15, 23, 42, 0.04);
      margin: 12px 0 18px;
    }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0 24px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
    th {{ background: #f6f6f6; text-align: left; }}
    code {{ background: #f2f2f2; padding: 2px 4px; border-radius: 4px; }}
    .chart {{ width: 100%; height: auto; display: block; }}
    .chart-title {{ font-size: 14px; font-weight: 700; fill: var(--ink); }}
    .legend {{ font-size: 12px; fill: var(--muted); }}
    .axis-label {{ font-size: 12px; fill: var(--ink); }}
    .rank {{ font-size: 11px; fill: var(--muted); }}
    .item {{ font-size: 11px; fill: var(--ink); }}
    .value {{ font-size: 11px; fill: var(--muted); }}
    .charts {{ margin: 10px 0 14px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>CTR Ranker Before/After (경량 ML 1단계)</h1>
    <p class="sub">표 + 그래프(Top-5 순위 이동)로 Before/After를 빠르게 확인합니다.</p>

    <div class="card">
      {_svg_summary_chart()}
    </div>

    <div class="card">
      <h2 style="margin: 0 0 8px;">Summary (Table)</h2>
      <table>
        {''.join(summary_rows)}
      </table>
    </div>

    {''.join(f'<div class="card">{s}</div>' for s in group_sections)}
  </div>
</body>
</html>
"""
    out_path.write_text(html_doc, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None, help="KST 기준 날짜(YYYY-MM-DD). 기본: 오늘")
    parser.add_argument("--in", dest="in_path", default=None, help="입력 JSON 경로 (기본값 사용 가능)")
    parser.add_argument("--max-groups", type=int, default=3)
    parser.add_argument(
        "--format",
        choices=["print", "html", "csv", "all"],
        default="print",
    )
    args = parser.parse_args(argv)

    date_str = str(args.date) if args.date else _kst_date_str()
    paths = default_paths(date_str=date_str)
    report_json = Path(args.in_path) if args.in_path else paths.report_json

    report = load_report(report_json)

    if args.format in ("print", "all"):
        print_report_tables(report, max_groups=int(args.max_groups))
    if args.format in ("csv", "all"):
        write_summary_csv(report, paths.out_summary_csv)
        write_top5_csv(report, paths.out_top5_csv)
    if args.format in ("html", "all"):
        write_html(report, paths.out_html)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
