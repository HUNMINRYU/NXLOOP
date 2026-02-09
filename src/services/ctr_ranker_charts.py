from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

KST = timezone(timedelta(hours=9))


@dataclass(frozen=True)
class ChartPaths:
    report_json: Path
    out_pdf: Path


def _kst_date_str(now_utc: datetime | None = None) -> str:
    now = now_utc or datetime.now(timezone.utc)
    return now.astimezone(KST).strftime("%Y-%m-%d")


def default_paths(*, date_str: str) -> ChartPaths:
    report_json = Path(f"outputs/ctr_ranker/reports/{date_str}-before-after.json")
    out_pdf = Path(f"outputs/ctr_ranker/charts/{date_str}-before-after.pdf")
    return ChartPaths(report_json=report_json, out_pdf=out_pdf)


def load_report(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("report JSON 최상위는 object(dict)여야 합니다.")
    return data


def _truncate(s: str, *, max_len: int) -> str:
    s = (s or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max(0, max_len - 1)] + "…"


def _draw_title(c: canvas.Canvas, *, text: str, x: float, y: float) -> None:
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, y, text)


def _draw_subtitle(c: canvas.Canvas, *, text: str, x: float, y: float) -> None:
    c.setFont("Helvetica", 10)
    c.setFillColor(HexColor("#475569"))
    c.drawString(x, y, text)
    c.setFillColor(HexColor("#0f172a"))


def _draw_summary_bars(
    c: canvas.Canvas,
    *,
    x: float,
    y: float,
    width: float,
    report: dict[str, Any],
) -> float:
    """
    Summary metrics를 단순 막대 그래프로 그린다.
    반환값은 다음 섹션을 시작할 y(아래쪽) 좌표이다.
    """
    k = int(report.get("k", 5))
    metrics = [
        (f"NDCG@{k}", float(report.get("ndcg_before") or 0.0), float(report.get("ndcg_after") or 0.0)),
        ("Spearman", float(report.get("spearman_before") or 0.0), float(report.get("spearman_after") or 0.0)),
        ("Top-1 hit", float(report.get("top1_before") or 0.0), float(report.get("top1_after") or 0.0)),
    ]
    max_val = max([1e-9, *[b for _, b, _ in metrics], *[a for _, _, a in metrics]])

    row_h = 18
    label_w = 90
    bar_w = width - label_w - 110
    before_color = HexColor("#94a3b8")
    after_color = HexColor("#0ea5e9")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "Summary (Before vs After)")
    y -= 14

    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor("#475569"))
    c.drawString(x + label_w, y, "Before")
    c.drawString(x + label_w + 60, y, "After")
    c.setFillColor(HexColor("#0f172a"))
    y -= 10

    for label, before, after in metrics:
        c.setFont("Helvetica", 9)
        c.drawString(x, y, label)

        bw = (before / max_val) * bar_w
        aw = (after / max_val) * bar_w

        c.setFillColor(before_color)
        c.rect(x + label_w, y - 3, bw, 6, stroke=0, fill=1)
        c.setFillColor(after_color)
        c.rect(x + label_w, y - 12, aw, 6, stroke=0, fill=1)

        c.setFillColor(HexColor("#0f172a"))
        c.setFont("Helvetica", 8)
        c.drawRightString(x + label_w + bar_w + 48, y, f"{before:.4f}")
        c.drawRightString(x + label_w + bar_w + 48, y - 9, f"{after:.4f}")

        y -= row_h

    return y - 8


def _draw_rank_shift_top5(
    c: canvas.Canvas,
    *,
    x: float,
    y: float,
    width: float,
    group: dict[str, Any],
) -> float:
    """
    Top-5(before/after) 기준으로 간단한 rank shift(슬로프) 차트를 그린다.
    """
    before = list(group.get("top5_before", []) or [])
    after = list(group.get("top5_after", []) or [])
    before_rank = {str(r.get("title", "")): i for i, r in enumerate(before, start=1)}
    after_rank = {str(r.get("title", "")): i for i, r in enumerate(after, start=1)}

    titles: list[str] = []
    for t in list(before_rank.keys()) + list(after_rank.keys()):
        if t and t not in titles:
            titles.append(t)

    left_x = x + 120
    right_x = x + width - 120
    row_h = 22
    top_y = y - 18

    def y_for_rank(r: int) -> float:
        rr = max(1, min(5, int(r)))
        return top_y - (rr - 1) * row_h

    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "Rank Shift (Top-5)")
    y -= 16

    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor("#475569"))
    c.drawCentredString(left_x, y, "Before")
    c.drawCentredString(right_x, y, "After")
    c.setFillColor(HexColor("#0f172a"))

    # grid + rank labels
    c.setStrokeColor(HexColor("#e5e7eb"))
    for r in range(1, 6):
        yy = y_for_rank(r)
        c.line(left_x, yy, right_x, yy)
        c.setFont("Helvetica", 8)
        c.setFillColor(HexColor("#475569"))
        c.drawRightString(left_x - 10, yy - 3, str(r))
        c.drawString(right_x + 6, yy - 3, str(r))
        c.setFillColor(HexColor("#0f172a"))

    # lines + nodes
    c.setStrokeColor(HexColor("#0ea5e9"))
    c.setFillColor(HexColor("#0ea5e9"))
    for t in titles:
        b = before_rank.get(t)
        a = after_rank.get(t)
        if b is None and a is None:
            continue

        if b is not None and a is not None:
            y0 = y_for_rank(b)
            y1 = y_for_rank(a)
            c.setLineWidth(1.5)
            c.line(left_x, y0, right_x, y1)

        # before node + label
        if b is not None:
            y0 = y_for_rank(b)
            c.circle(left_x, y0, 3, stroke=0, fill=1)
            c.setFont("Helvetica", 7)
            c.setFillColor(HexColor("#0f172a"))
            c.drawRightString(left_x - 6, y0 - 3, _truncate(t, max_len=52))
            c.setFillColor(HexColor("#0ea5e9"))

        # after node + label
        if a is not None:
            y1 = y_for_rank(a)
            c.circle(right_x, y1, 3, stroke=0, fill=1)
            c.setFont("Helvetica", 7)
            c.setFillColor(HexColor("#0f172a"))
            c.drawString(right_x + 6, y1 - 3, _truncate(t, max_len=52))
            c.setFillColor(HexColor("#0ea5e9"))

    c.setFillColor(HexColor("#0f172a"))
    c.setLineWidth(1)
    return top_y - row_h * 5 - 8


def write_pdf(report: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    page_w, page_h = A4
    margin = 48

    c = canvas.Canvas(str(out_path), pagesize=A4)
    c.setFillColor(HexColor("#0f172a"))

    # Cover / Summary page
    y = page_h - margin
    _draw_title(c, text="CTR Ranker Before/After (경량 ML 1단계)", x=margin, y=y)
    y -= 18
    _draw_subtitle(
        c,
        text="HTML 대신 PDF 그래프(Report JSON 기반)로 출력합니다.",
        x=margin,
        y=y,
    )
    y -= 26
    y = _draw_summary_bars(c, x=margin, y=y, width=page_w - margin * 2, report=report)
    c.showPage()

    # Group pages
    groups = list(report.get("groups", []) or [])
    for g in groups:
        gid = str(g.get("group_id", "") or "").strip() or "(unknown)"

        y = page_h - margin
        _draw_title(c, text=f"Group: {gid}", x=margin, y=y)
        y -= 16
        _draw_subtitle(
            c,
            text="Top-5 순위 이동(슬로프 차트). 동일 title만 연결됩니다.",
            x=margin,
            y=y,
        )
        y -= 28
        _draw_rank_shift_top5(c, x=margin, y=y, width=page_w - margin * 2, group=g)
        c.showPage()

    c.save()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None, help="KST 기준 날짜(YYYY-MM-DD). 기본: 오늘")
    parser.add_argument("--in", dest="in_path", default=None, help="입력 JSON 경로 (기본값 사용 가능)")
    parser.add_argument("--out", dest="out_path", default=None, help="출력 PDF 경로 (기본값 사용 가능)")
    args = parser.parse_args(argv)

    date_str = str(args.date) if args.date else _kst_date_str()
    paths = default_paths(date_str=date_str)

    in_path = Path(args.in_path) if args.in_path else paths.report_json
    out_path = Path(args.out_path) if args.out_path else paths.out_pdf

    report = load_report(in_path)
    write_pdf(report, out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

