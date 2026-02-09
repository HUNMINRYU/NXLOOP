from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps import CurrentUser, require_role
from config.dependencies import get_services
from infrastructure.database.connection import get_db_session
from services.ctr_ranker_approval_service import CTRRankerApprovalService

router = APIRouter(prefix="/ctr-ranker", tags=["ctr-ranker"])


class ImportRunRequest(BaseModel):
    product_name: str = Field(..., min_length=1)
    report_date: date

    # 운영에서는 GCS가 기본. 로컬 개발이면 비워두고 default path 사용 가능.
    raw_dataset_gcs_path: str | None = None
    topk_csv_gcs_path: str | None = None
    report_json_gcs_path: str | None = None

    # 로컬 fallback (WSL/로컬 실행 시)
    raw_dataset_local_path: str | None = None
    topk_csv_local_path: str | None = None

    mode: str = "youtube"


class ApproveRequest(BaseModel):
    candidate_id: int
    note: str | None = None


def _read_summary_metrics_csv(path: str) -> dict[str, dict[str, float]]:
    p = Path(path)
    if not p.is_file():
        return {}
    out: dict[str, dict[str, float]] = {}
    with p.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            metric = (row.get("metric") or "").strip()
            if not metric:
                continue
            try:
                before = float((row.get("before") or "").strip() or "nan")
                after = float((row.get("after") or "").strip() or "nan")
            except ValueError:
                continue
            out[metric] = {"before": before, "after": after}
    return out


def _read_local_text(path: str) -> str:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(path)
    return p.read_text(encoding="utf-8")


def _read_local_json(path: str) -> dict[str, Any]:
    return json.loads(_read_local_text(path))


@router.post("/runs/import")
async def import_run(
    request: ImportRunRequest,
    user: Annotated[CurrentUser, Depends(require_role(["admin", "editor"]))],
    session: Annotated[Any, Depends(get_db_session)],
):
    services = get_services()
    storage = services.storage_service

    # 1) raw dataset 로드
    raw_dataset: dict[str, Any] | None = None
    raw_path = request.raw_dataset_gcs_path or request.raw_dataset_local_path
    if request.raw_dataset_gcs_path:
        raw_dataset = storage.download_json(request.raw_dataset_gcs_path)  # type: ignore[assignment]
    elif request.raw_dataset_local_path:
        raw_dataset = _read_local_json(request.raw_dataset_local_path)
    else:
        # 관례: outputs/ctr_ranker/datasets/{date}-youtube-raw.json
        default = f"outputs/ctr_ranker/datasets/{request.report_date.isoformat()}-youtube-raw.json"
        raw_path = default
        raw_dataset = _read_local_json(default)

    if not raw_dataset:
        raise HTTPException(status_code=400, detail="raw dataset을 로드하지 못했습니다.")

    # 2) topK CSV 로드
    topk_csv_text: str | None = None
    topk_path = request.topk_csv_gcs_path or request.topk_csv_local_path
    if request.topk_csv_gcs_path:
        topk_csv_text = storage.download_text(request.topk_csv_gcs_path)  # type: ignore[assignment]
    elif request.topk_csv_local_path:
        topk_csv_text = _read_local_text(request.topk_csv_local_path)
    else:
        default = f"outputs/ctr_ranker/reports/{request.report_date.isoformat()}-top5.csv"
        topk_path = default
        topk_csv_text = _read_local_text(default)

    if not topk_csv_text:
        raise HTTPException(status_code=400, detail="topK CSV를 로드하지 못했습니다.")

    # 3) (선택) 요약 메트릭 로드 (로컬 fallback)
    metrics: dict[str, Any] = {}
    default_summary = f"outputs/ctr_ranker/reports/{request.report_date.isoformat()}-summary.csv"
    metrics.update(_read_summary_metrics_csv(default_summary))

    svc = CTRRankerApprovalService(session)
    try:
        result = await svc.import_from_raw_and_topk_csv(
            product_name=request.product_name,
            report_date=request.report_date,
            raw_dataset=raw_dataset,
            topk_csv_text=topk_csv_text,
            mode=request.mode,
            raw_dataset_path=raw_path,
            topk_csv_path=topk_path,
            report_json_path=request.report_json_gcs_path,
            metrics=metrics,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {"run_id": result.run_id, "candidate_count": result.candidate_count}


@router.get("/runs")
async def list_runs(
    product_name: str,
    user: Annotated[CurrentUser, Depends(require_role(["admin", "editor"]))],
    session: Annotated[Any, Depends(get_db_session)],
):
    svc = CTRRankerApprovalService(session)
    runs = await svc.list_runs(product_name=product_name, limit=20)
    return {
        "runs": [
            {
                "id": r.id,
                "product_name": r.product_name,
                "report_date": r.report_date.isoformat(),
                "mode": r.mode,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "metrics": json.loads(r.metrics_json or "{}"),
            }
            for r in runs
        ]
    }


@router.get("/runs/{run_id}/candidates")
async def list_candidates(
    run_id: str,
    user: Annotated[CurrentUser, Depends(require_role(["admin", "editor"]))],
    session: Annotated[Any, Depends(get_db_session)],
):
    svc = CTRRankerApprovalService(session)
    candidates = await svc.list_candidates(run_id=run_id, limit=50)
    approval = await svc.get_approval(run_id=run_id)
    approved_candidate_id = approval.candidate_id if approval else None

    before_top5 = [c for c in candidates if c.baseline_rank is not None and c.baseline_rank <= 5]
    after_top5 = [c for c in candidates if c.after_rank is not None and c.after_rank <= 5]
    before_titles = {c.title for c in before_top5}
    after_titles = {c.title for c in after_top5}
    entered = sorted(after_titles - before_titles)
    dropped = sorted(before_titles - after_titles)
    top1_before = next((c for c in candidates if c.baseline_rank == 1), None)
    top1_after = next((c for c in candidates if c.after_rank == 1), None)
    top1_changed = bool(top1_before and top1_after and top1_before.title != top1_after.title)

    return {
        "summary": {
            "top1_changed": top1_changed,
            "entered_count": len(entered),
            "dropped_count": len(dropped),
            "entered_titles": entered,
            "dropped_titles": dropped,
            "top1_before_title": top1_before.title if top1_before else None,
            "top1_after_title": top1_after.title if top1_after else None,
        },
        "approved_candidate_id": approved_candidate_id,
        "candidates": [
            {
                "id": c.id,
                "title": c.title,
                "video_id": c.video_id,
                "thumbnail_url": c.thumbnail_url,
                "baseline_rank": c.baseline_rank,
                "baseline_score": c.baseline_score,
                "after_rank": c.after_rank,
                "after_score": c.after_score,
                "proxy_score": c.proxy_score,
            }
            for c in candidates
        ],
    }


@router.post("/runs/{run_id}/approve")
async def approve_candidate(
    run_id: str,
    request: ApproveRequest,
    user: Annotated[CurrentUser, Depends(require_role(["admin", "editor"]))],
    session: Annotated[Any, Depends(get_db_session)],
):
    svc = CTRRankerApprovalService(session)
    try:
        approval = await svc.approve(
            run_id=run_id,
            candidate_id=request.candidate_id,
            approved_by_user_id=getattr(user, "id", None),
            note=request.note,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {
        "approval": {
            "id": approval.id,
            "run_id": approval.run_id,
            "candidate_id": approval.candidate_id,
            "approved_by_user_id": approval.approved_by_user_id,
            "note": approval.note,
            "approved_at": approval.approved_at.isoformat() if approval.approved_at else None,
        }
    }
