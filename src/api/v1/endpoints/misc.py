import asyncio
import json
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from api.deps import require_tier
from config.dependencies import get_services
from config.settings import get_settings
from schemas.requests import LeadRequest, RefreshUrlRequest
from utils.file_store import ensure_output_dir
from utils.logger import log_feature_end, log_feature_fail, log_feature_start

router = APIRouter()

# 평가/발표용: Nexloop에서 사용하는 GCP 서비스 요약 (문서·헬스 응답용)
GCP_SERVICES_USED = [
    "Cloud Run",
    "Cloud SQL",
    "GCS",
    "Secret Manager",
    "Vertex AI",
    "Cloud Scheduler",
]


@router.get("/health")
async def health_check():
    """헬스 체크. 사용 중인 GCP 서비스 요약 포함 (평가/발표용)."""
    log_feature_start("health_check", "")
    log_feature_end("health_check")
    return {
        "status": "ok",
        "message": "Nexloop API is running",
        "gcp_services": GCP_SERVICES_USED,
    }


@router.head("/health")
async def health_check_head():
    """헬스 체크(HEAD). Cloud Run/모니터링에서 HEAD 요청이 들어와도 405가 나지 않게 한다."""
    # HEAD 응답은 body 없이 200만 반환하면 충분하다.
    log_feature_start("health_check", "HEAD")
    log_feature_end("health_check")
    return None


@router.post("/leads")
async def create_lead(request: LeadRequest):
    log_feature_start("leads_capture", "")
    if "@" not in request.email:
        log_feature_fail("leads_capture", "invalid email")
        raise HTTPException(status_code=400, detail="Invalid email")
    try:
        out_dir = ensure_output_dir()
        lead_path = out_dir / "leads.jsonl"
        payload = {
            "email": request.email,
            "created_at": datetime.now().isoformat(),
        }

        def _append_lead_sync(path: str, data: dict[str, Any]) -> None:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")

        await asyncio.to_thread(_append_lead_sync, str(lead_path), payload)
        log_feature_end("leads_capture")
        return {"status": "ok"}
    except Exception as e:
        log_feature_fail("leads_capture", str(e)[:200])
        raise HTTPException(status_code=500, detail="Failed to capture lead") from e




@router.post("/refresh-url")
async def refresh_signed_url(request: RefreshUrlRequest):
    log_feature_start("refresh_signed_url", "")
    services = get_services()
    storage = services.storage_service

    raw_path = request.gcs_path.strip()
    path = raw_path
    if raw_path.startswith("gs://"):
        parts = raw_path[5:].split("/", 1)
        if len(parts) == 2:
            path = parts[1]
    url = storage.get_signed_url(path)
    if not url:
        log_feature_fail("refresh_signed_url", "failed to generate URL")
        raise HTTPException(status_code=404, detail="Failed to generate signed URL")
    log_feature_end("refresh_signed_url")
    return {"url": url}


@router.get("/search/discovery")
async def search_discovery(
    q: str,
    user: Annotated[Any, Depends(require_tier("PRO"))],
    background_tasks: BackgroundTasks,
    max_results: int = 5,
):
    log_feature_start("search_discovery", "")
    try:
        services = get_services()
        settings = get_settings()
        data_store_id = settings.rag_data_stores.get(getattr(user, "role", ""))
        results = await services.discovery_engine_client.search(
            q,
            max_results=max_results,
            data_store_id=data_store_id,
        )
        background_tasks.add_task(
            services.rag_ingestion_service.ingest_search_log,
            q,
            results,
            user,
        )
        log_feature_end("search_discovery", extra_detail=f"results={len(results)}")
        return {"results": results}
    except Exception as e:
        log_feature_fail("search_discovery", str(e)[:200])
        raise HTTPException(status_code=500, detail="Discovery search failed") from e
