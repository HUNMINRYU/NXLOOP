import asyncio
import json
from datetime import datetime
from time import perf_counter
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse

from api.deps import CurrentUser, require_role, require_tier
from config.dependencies import get_services
from config.products import get_product_by_name
from core.audit import record_audit_log
from core.state import PIPELINE_RESULTS, PIPELINE_STATUS
from infrastructure.database.connection import get_db_session
from infrastructure.database.models import PipelineTask
from schemas.requests import (
    AnalysisTaskRequest,
    ApprovalStatusRequest,
    CTRPredictRequest,
    NotionExportRequest,
    PipelineRequest,
    PipelineSelectOutputRequest,
)
from services.pipeline_runner import execute_pipeline_task, init_pipeline_status

# from utils.file_store import ensure_output_dir  <-- keeping if used later
from utils.file_store import ensure_output_dir
from utils.gcs_store import build_gcs_prefix, detect_video_ext, gcs_url_for
from utils.log_throttle import should_log_throttled
from utils.logger import log_feature_end, log_feature_fail, log_feature_start

router = APIRouter()


def _get_task_status_and_result(task_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    status = PIPELINE_STATUS.get(task_id)
    result = PIPELINE_RESULTS.get(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    if not result:
        raise HTTPException(status_code=404, detail="Task result not found")
    return status, result


def _extract_collected_data(result: dict[str, Any]) -> dict[str, Any]:
    collected = result.get("collected_data") or {}
    return collected if isinstance(collected, dict) else {}


def _load_pipeline_result_dict(task_id: str) -> tuple[str, dict[str, Any], bool]:
    """in-memory 또는 history 메타데이터에서 pipeline result를 dict로 로드한다.

    Returns:
        (source, data, is_in_memory)
    """
    if task_id in PIPELINE_RESULTS:
        return "memory", PIPELINE_RESULTS[task_id], True

    services = get_services()
    history = services.history_service.load_history(task_id)
    if history:
        return "history", history.model_dump(), False

    raise HTTPException(status_code=404, detail="Task result not found")


@router.get("/history")
async def get_pipeline_history(user: CurrentUser):
    log_feature_start("pipeline_history")
    services = get_services()
    history_items = services.history_service.get_history_list()
    pipeline_task_service = getattr(services, "pipeline_task_service", None)

    history_tasks = []
    for item in history_items:
        executed_at = item.get("executed_at", "")
        history_tasks.append(
            {
                "task_id": item.get("id"),
                "product": item.get("product_name", ""),
                "status": "success" if item.get("success") else "failed",
                "created_at": executed_at,
                "updated_at": executed_at,
            }
        )

    in_memory_tasks = [
        {
            "task_id": task.get("task_id"),
            "product": task.get("product"),
            "status": task.get("status"),
            "created_at": task.get("created_at"),
            "updated_at": task.get("updated_at"),
        }
        for task in PIPELINE_STATUS.values()
    ]

    tasks_by_id = {
        task["task_id"]: task for task in in_memory_tasks if task.get("task_id")
    }
    for task in history_tasks:
        task_id = task.get("task_id")
        if task_id and task_id not in tasks_by_id:
            tasks_by_id[task_id] = task

    if pipeline_task_service is not None:
        db_tasks = await pipeline_task_service.list_recent(limit=50)
        for task in db_tasks:
            task_id = task.get("task_id")
            if task_id and task_id not in tasks_by_id:
                tasks_by_id[task_id] = task

    tasks = list(tasks_by_id.values())
    tasks.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
    log_feature_end("pipeline_history")
    return {"tasks": tasks}


@router.get("/status/{task_id}")
async def get_pipeline_status(task_id: str):
    feature = "pipeline_status"
    should_log = should_log_throttled(f"{feature}:{task_id}", interval_sec=10.0)

    def _start() -> None:
        if should_log:
            log_feature_start(feature, task_id)

    def _end(extra_detail: str = "") -> None:
        if should_log:
            log_feature_end(feature, extra_detail=extra_detail)

    _start()
    status = PIPELINE_STATUS.get(task_id)
    if not status:
        services = get_services()
        pipeline_task_service = getattr(services, "pipeline_task_service", None)
        if pipeline_task_service is not None:
            db_status = await pipeline_task_service.get_status(task_id)
            if db_status:
                _end(extra_detail="from_db")
                return db_status

        # Cloud Run 다중 인스턴스에서 in-memory 상태가 다른 인스턴스로 라우팅되면 404가 섞여 보일 수 있다.
        # 프론트 폴링 UX를 깨지 않도록 "routing miss" 형태로 완화한다.
        log_feature_fail(feature, f"Task not found (routing miss?): {task_id}")
        _end(extra_detail="routing_miss")
        return {
            "status": "pending",
            "message": "작업 상태를 다른 인스턴스에서 처리 중입니다. 잠시 후 다시 확인하세요.",
            "progress": {
                "percentage": 0,
                "message": "라우팅 재시도 중",
                "step": "routing_miss",
            },
            "task_id": task_id,
            "process_logs": [],
        }
    _end()
    return status


@router.get("/status-stream/{task_id}")
async def stream_pipeline_status(task_id: str):
    async def event_generator():
        services = get_services()
        pipeline_task_service = getattr(services, "pipeline_task_service", None)
        routing_miss_count = 0
        while True:
            status = PIPELINE_STATUS.get(task_id)
            if not status and pipeline_task_service is not None:
                status = await pipeline_task_service.get_status(task_id)
            if not status:
                # Cloud Run 다중 인스턴스에서 아직 DB 스냅샷이 없으면 잠깐 비어 있을 수 있다.
                # UX를 위해 짧게 재시도하며, 그동안은 routing_miss 상태를 흘려준다.
                routing_miss_count += 1
                if routing_miss_count <= 10:
                    fallback = {
                        "status": "pending",
                        "message": "작업 상태를 다른 인스턴스에서 처리 중입니다. 잠시 후 다시 확인하세요.",
                        "progress": {
                            "percentage": 0,
                            "message": "라우팅 재시도 중",
                            "step": "routing_miss",
                        },
                        "task_id": task_id,
                        "process_logs": [],
                    }
                    # status payload에 datetime 등이 포함될 수 있어 안전 직렬화 사용
                    yield f"data: {PipelineTask.dumps(fallback)}\n\n"
                    await asyncio.sleep(1)
                    continue
                yield "event: error\ndata: {}\n\n"
                break
            # status payload에 datetime 등이 포함될 수 있어 안전 직렬화 사용
            yield f"data: {PipelineTask.dumps(status)}\n\n"
            if status.get("status") in {"success", "failed"}:
                break
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/result/{task_id}")
async def get_pipeline_result(task_id: str, user: CurrentUser):
    log_feature_start("pipeline_result", task_id)
    status = PIPELINE_STATUS.get(task_id)
    result = PIPELINE_RESULTS.get(task_id)
    if not status:
        services = get_services()
        pipeline_task_service = getattr(services, "pipeline_task_service", None)
        if pipeline_task_service is not None:
            db_result = await pipeline_task_service.get_result(task_id)
            if db_result:
                db_status = await pipeline_task_service.get_status(task_id)
                if not db_status:
                    executed_at = db_result.get("executed_at") or ""
                    db_status = {
                        "task_id": task_id,
                        "status": "success" if db_result.get("success") else "failed",
                        "product": db_result.get("product_name", ""),
                        "message": "DB 결과",
                        "progress": {
                            "message": "DB 로드",
                            "percentage": 100 if db_result.get("success") else 0,
                            "step": "completed" if db_result.get("success") else "failed",
                        },
                        "created_at": executed_at,
                        "updated_at": executed_at,
                    }
                log_feature_end("pipeline_result", extra_detail="from_db")
                return {"status": db_status, "result": db_result}

        history_record = services.history_service.load_history(task_id)
        if history_record:
            record_data = history_record.model_dump()
            log_feature_end("pipeline_result", extra_detail="from_history")
            return {
                "status": {
                    "task_id": task_id,
                    "status": "success" if record_data.get("success") else "failed",
                    "product": record_data.get("product_name", ""),
                    "message": "히스토리 결과",
                    "progress": {
                        "message": "히스토리 로드",
                        "percentage": 100 if record_data.get("success") else 0,
                        "step": "completed" if record_data.get("success") else "failed",
                    },
                    "created_at": record_data.get("executed_at", ""),
                    "updated_at": record_data.get("executed_at", ""),
                },
                "result": record_data,
            }
        log_feature_fail("pipeline_result", f"Task not found: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")
    log_feature_end("pipeline_result")
    return {
        "status": status,
        "result": result,
    }


@router.post("/run")
async def trigger_pipeline(
    request: PipelineRequest,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
):
    log_feature_start("pipeline_run", request.product_name)
    product = get_product_by_name(request.product_name)
    if not product:
        log_feature_fail("pipeline_run", f"Product '{request.product_name}' not found")
        raise HTTPException(
            status_code=404, detail=f"Product '{request.product_name}' not found"
        )

    task_id = str(uuid4())
    init_pipeline_status(task_id, request.product_name)
    background_tasks.add_task(execute_pipeline_task, request, task_id)

    status = PIPELINE_STATUS.get(task_id) or {}
    process_logs = status.get("process_logs") if isinstance(status, dict) else None
    if not isinstance(process_logs, list):
        process_logs = []

    log_feature_end("pipeline_run", extra_detail=f"task_id={task_id}")
    return {
        "status": "triggered",
        "task_id": task_id,
        "product": request.product_name,
        "process_logs": process_logs,
        "steps": process_logs,
        "timestamp": datetime.now().isoformat(),
    }


@router.patch("/result/{task_id}/status")
async def update_pipeline_status_endpoint(
    task_id: str,
    request: ApprovalStatusRequest,
    user: Annotated[CurrentUser, Depends(require_role(["admin", "approver"]))],
    session: Annotated[Any, Depends(get_db_session)],
):
    log_feature_start("pipeline_update_approval", f"{task_id} -> {request.status}")
    allowed = {"draft", "pending_review", "approved", "rejected"}
    if request.status not in allowed:
        log_feature_fail("pipeline_update_approval", "Invalid status")
        raise HTTPException(status_code=400, detail="Invalid status")

    def _append_audit(result_obj: dict[str, Any]) -> None:
        trail = result_obj.get("audit_trail")
        if not isinstance(trail, list):
            trail = []
        trail.append(
            {
                "action": f"status:{request.status}",
                "by": getattr(user, "email", "unknown"),
                "at": datetime.now().isoformat(),
            }
        )
        result_obj["audit_trail"] = trail

    if task_id in PIPELINE_RESULTS:
        result = PIPELINE_RESULTS[task_id]
        result["approval_status"] = request.status
        _append_audit(result)
        PIPELINE_RESULTS[task_id] = result
        services = get_services()
        pipeline_task_service = getattr(services, "pipeline_task_service", None)
        if pipeline_task_service is not None:
            await pipeline_task_service.upsert_result(task_id, result)
        await record_audit_log(
            session=session,
            action="update_approval_status",
            actor_email=getattr(user, "email", "unknown"),
            actor_role=getattr(user, "role", "editor"),
            entity_type="pipeline_result",
            entity_id=str(task_id),
            metadata={"status": request.status},
        )
        log_feature_end("pipeline_update_approval", extra_detail="in_memory")
        return {"status": request.status}

    meta_dir = ensure_output_dir() / "metadata"
    file_path = meta_dir / f"{task_id}.json"
    if file_path.exists():
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            data["approval_status"] = request.status
            _append_audit(data)
            file_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            await record_audit_log(
                session=session,
                action="update_approval_status",
                actor_email=getattr(user, "email", "unknown"),
                actor_role=getattr(user, "role", "editor"),
                entity_type="pipeline_result",
                entity_id=str(task_id),
                metadata={"status": request.status},
            )
            log_feature_end("pipeline_update_approval", extra_detail="history_file")
            return {"status": request.status}
        except Exception as e:
            log_feature_fail("pipeline_update_approval", str(e))
            raise HTTPException(
                status_code=500, detail="Failed to update history"
            ) from e

    log_feature_fail("pipeline_update_approval", f"Task result not found: {task_id}")
    raise HTTPException(status_code=404, detail="Task result not found")


@router.post("/result/{task_id}/select-output")
async def select_pipeline_output_endpoint(
    task_id: str,
    request: PipelineSelectOutputRequest,
    user: CurrentUser,
):
    """Create 단계 산출물(썸네일/비디오)을 1개 채택해 다음 단계 입력으로 사용한다.

    - in-memory PIPELINE_RESULTS가 있으면 거기에 기록
    - 없으면 history metadata 파일에 기록
    """
    feature = "pipeline_select_output"
    t0 = perf_counter()
    log_feature_start(feature, f"{request.kind}")

    def _set_selected(result_obj: dict[str, Any]) -> None:
        selected = result_obj.get("selected_outputs")
        if not isinstance(selected, dict):
            selected = {}
        selected[request.kind] = {
            "url": request.url,
            "meta": request.meta or {},
            "selected_by": getattr(user, "email", "unknown"),
            "selected_at": datetime.now().isoformat(),
        }
        result_obj["selected_outputs"] = selected

    try:
        if task_id in PIPELINE_RESULTS:
            result = PIPELINE_RESULTS[task_id]
            _set_selected(result)
            PIPELINE_RESULTS[task_id] = result
            services = get_services()
            pipeline_task_service = getattr(services, "pipeline_task_service", None)
            if pipeline_task_service is not None:
                await pipeline_task_service.upsert_result(task_id, result)
            log_feature_end(
                feature,
                perf_counter() - t0,
                extra_detail=f"source=memory kind={request.kind}",
            )
            return {"selected_outputs": result.get("selected_outputs")}

        meta_dir = ensure_output_dir() / "metadata"
        file_path = meta_dir / f"{task_id}.json"
        if file_path.exists():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                _set_selected(data)
                file_path.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                log_feature_end(
                    feature,
                    perf_counter() - t0,
                    extra_detail=f"source=history kind={request.kind}",
                )
                return {"selected_outputs": data.get("selected_outputs")}
            except Exception as e:
                log_feature_fail(feature, str(e))
                raise HTTPException(
                    status_code=500, detail="Failed to update history"
                ) from e

        log_feature_fail(feature, "Task result not found")
        raise HTTPException(status_code=404, detail="Task result not found")
    except HTTPException:
        # 이미 fail 로그를 남겼거나, 기존 예외를 유지한다.
        raise
    except Exception as e:
        log_feature_fail(feature, str(e))
        raise


@router.post("/result/{task_id}/generate-video-from-selected-thumbnail")
async def generate_video_from_selected_thumbnail_endpoint(
    task_id: str,
    user: Annotated[Any, Depends(require_tier("PRO"))],
):
    """선택(채택)된 썸네일을 Start Frame으로 사용해 I2V 비디오를 재생성하고, 그 결과를 자동 채택한다."""
    feature = "pipeline_generate_video_selected_thumbnail"
    t0 = perf_counter()
    log_feature_start(feature, task_id)
    try:
        services = get_services()
        storage = services.storage_service
        storage.ensure_bucket()

        source, data, in_memory = _load_pipeline_result_dict(task_id)
        selected = data.get("selected_outputs")
        if not isinstance(selected, dict) or "thumbnail" not in selected:
            raise HTTPException(
                status_code=400,
                detail="선택된 썸네일이 없습니다. (먼저 썸네일 채택 필요)",
            )

        thumb = selected.get("thumbnail") or {}
        if not isinstance(thumb, dict):
            raise HTTPException(
                status_code=400, detail="선택된 썸네일 정보가 올바르지 않습니다."
            )

        thumb_url = thumb.get("url")
        if not isinstance(thumb_url, str) or not thumb_url.strip():
            raise HTTPException(status_code=400, detail="선택된 썸네일 URL이 없습니다.")

        # 1) 썸네일 bytes 다운로드 (signed URL/https 기준)
        # async endpoint에서 블로킹 I/O를 피하기 위해 thread로 분리한다.
        try:
            import urllib.request

            def _download_bytes(url: str) -> bytes:
                with urllib.request.urlopen(url, timeout=15.0) as res:
                    return res.read()

            image_bytes = await asyncio.to_thread(_download_bytes, thumb_url)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"썸네일 다운로드 실패: {e}"
            ) from e

        product_name = data.get("product_name") or data.get("product") or ""
        if not isinstance(product_name, str):
            product_name = str(product_name or "")

        product = get_product_by_name(product_name) if product_name else None
        product_dict = (
            product.model_dump()
            if product and hasattr(product, "model_dump")
            else (product.__dict__ if product else {"name": product_name})
        )

        # 2) 훅 텍스트 결정: 선택 썸네일 meta > strategy 훅 > 제품명
        hook_text = None
        meta = thumb.get("meta")
        if isinstance(meta, dict) and isinstance(meta.get("hook_text"), str):
            hook_text = meta.get("hook_text")
        if not hook_text:
            strategy = data.get("strategy") or {}
            if isinstance(strategy, dict):
                hooks = strategy.get("hook_suggestions", [])
                if isinstance(hooks, list) and hooks:
                    first = hooks[0]
                    if isinstance(first, dict) and isinstance(first.get("hook"), str):
                        hook_text = first.get("hook")
                    elif isinstance(first, str):
                        hook_text = first
        hook_text = (hook_text or f"{product_dict.get('name', '제품')}!").strip()

        # 3) 프롬프트 생성: (가능하면) Vision-Narrative -> fallback marketing prompt
        try:
            prompt = services.video_service.generate_story_prompt_from_image(
                image_bytes=image_bytes,
                product=product_dict,
                hook_text=hook_text,
                mode="single",
            )
        except Exception:
            insights = {"hook": hook_text, "style": "commercial", "mood": "dramatic"}
            prompt = services.video_service.create_marketing_prompt(
                product_dict, insights, hook_text
            )

        # 4) I2V 생성 + GCS 업로드 + 자동 채택(selected_outputs.video)
        duration_seconds = 8
        config = data.get("config") or {}
        if isinstance(config, dict):
            try:
                duration_seconds = int(config.get("video_duration") or 8)
            except Exception:
                duration_seconds = 8

        video_result = services.video_service.generate_from_image(
            image_bytes=image_bytes,
            prompt=prompt,
            duration_seconds=duration_seconds,
        )

        if not video_result:
            raise HTTPException(status_code=500, detail="비디오 생성 실패: 결과가 비어 있습니다.")

        video_bytes: bytes | None = video_result if isinstance(video_result, bytes) else None
        if not video_bytes:
            raise HTTPException(status_code=500, detail=f"비디오 생성 실패: {video_result}")

        ext = detect_video_ext(video_bytes)
        prefix = build_gcs_prefix(product_dict, "pipeline")
        gcs_path = f"{prefix}/video_selected_thumb{ext}"
        storage.upload(
            data=video_bytes,
            path=gcs_path,
            content_type="video/mp4" if ext == ".mp4" else "application/octet-stream",
        )
        video_url = gcs_url_for(storage, gcs_path)

        # result dict 업데이트
        generated = data.get("generated_content")
        if not isinstance(generated, dict):
            generated = {}
        generated["video_url"] = video_url
        data["generated_content"] = generated

        selected["video"] = {
            "url": video_url,
            "meta": {
                "source": "selected_thumbnail_i2v",
                "duration_seconds": duration_seconds,
            },
            "selected_by": getattr(user, "email", "unknown"),
            "selected_at": datetime.now().isoformat(),
        }
        data["selected_outputs"] = selected

        # 저장
        if in_memory:
            PIPELINE_RESULTS[task_id] = data
            services = get_services()
            pipeline_task_service = getattr(services, "pipeline_task_service", None)
            if pipeline_task_service is not None and isinstance(data, dict):
                await pipeline_task_service.upsert_result(task_id, data)
        else:
            meta_dir = ensure_output_dir() / "metadata"
            file_path = meta_dir / f"{task_id}.json"
            if file_path.exists():
                file_path.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

        log_feature_end(
            feature,
            perf_counter() - t0,
            extra_detail=f"gcs_path={gcs_path}",
        )
        return {
            "video_url": video_url,
            "gcs_path": gcs_path,
            "selected_outputs": data.get("selected_outputs"),
            "source": source,
        }
    except HTTPException as e:
        log_feature_fail(feature, str(e.detail))
        raise
    except Exception as e:
        log_feature_fail(feature, str(e))
        raise


@router.post("/analysis/strategy")
async def analyze_strategy(
    request: AnalysisTaskRequest,
    user: Annotated[Any, Depends(require_tier("PRO"))],
):
    services = get_services()
    log_feature_start("analysis_strategy", request.task_id)
    status, result = _get_task_status_and_result(request.task_id)
    strategy = result.get("strategy")
    if strategy:
        log_feature_end("analysis_strategy", extra_detail="cached")
        return {"strategy": strategy}

    collected = _extract_collected_data(result)
    youtube_data = collected.get("youtube_data", {})
    naver_data = collected.get("naver_data", {})
    top_insights = collected.get("top_insights", [])
    product_name = status.get("product") or result.get("product_name", "")
    if not product_name:
        log_feature_fail("analysis_strategy", "Product name not found")
        raise HTTPException(status_code=400, detail="Product name not found")

    strategy = services.marketing_service.analyze_data(
        youtube_data=youtube_data,
        naver_data=naver_data,
        product_name=product_name,
        top_insights=top_insights,
    )
    if request.task_id in PIPELINE_RESULTS:
        PIPELINE_RESULTS[request.task_id]["strategy"] = strategy
        pipeline_task_service = getattr(services, "pipeline_task_service", None)
        if pipeline_task_service is not None:
            await pipeline_task_service.upsert_result(
                request.task_id, PIPELINE_RESULTS[request.task_id]
            )
    log_feature_end("analysis_strategy")
    return {"strategy": strategy}


@router.post("/analysis/comments/basic")
async def analyze_comments_basic(request: AnalysisTaskRequest):
    log_feature_start("analysis_comments_basic", request.task_id)
    services = get_services()
    _, result = _get_task_status_and_result(request.task_id)
    collected = _extract_collected_data(result)
    youtube_data = collected.get("youtube_data", {})
    comments = youtube_data.get("comments", [])
    if not comments:
        log_feature_fail("analysis_comments_basic", "No comments")
        raise HTTPException(status_code=400, detail="No comments available")
    analysis = services.comment_analysis_service.analyze_comments(comments)
    log_feature_end("analysis_comments_basic")
    return {"analysis": analysis}


@router.post("/analysis/comments/deep")
async def analyze_comments_deep(
    request: AnalysisTaskRequest,
    user: Annotated[Any, Depends(require_tier("PRO"))],
):
    log_feature_start("analysis_comments_deep", request.task_id)
    services = get_services()
    _, result = _get_task_status_and_result(request.task_id)
    collected = _extract_collected_data(result)
    youtube_data = collected.get("youtube_data", {})
    comments = youtube_data.get("comments", [])
    if not comments:
        log_feature_fail("analysis_comments_deep", "No comments")
        raise HTTPException(status_code=400, detail="No comments available")
    analysis = services.comment_analysis_service.analyze_with_ai(comments)
    log_feature_end("analysis_comments_deep")
    return {"analysis": analysis}


@router.post("/analysis/ctr-predict")
async def predict_ctr(
    request: CTRPredictRequest,
    user: Annotated[Any, Depends(require_tier("PRO"))],
):
    log_feature_start(
        "ctr_predict",
        f"task_id={request.task_id} title_len={len(request.title or '')} "
        f"thumb_desc_len={len(request.thumbnail_description or '')} "
        f"competitors={len(request.competitor_titles or [])}",
    )
    services = get_services()
    _, result = _get_task_status_and_result(request.task_id)
    collected = _extract_collected_data(result)
    top_insights = collected.get("top_insights", [])
    log_feature_start("ctr_predict_input", f"top_insights={len(top_insights)}")
    log_feature_end("ctr_predict_input")
    try:
        log_feature_start("ctr_predict_ai", "predict_with_ai")
        ai_prediction = await services.ctr_predictor.predict_with_ai(
            title=request.title,
            category="marketing",
            top_insights=top_insights,
        )
        log_feature_end(
            "ctr_predict_ai",
            extra_detail=f"keys={','.join(sorted(ai_prediction.keys()))[:120]}",
        )
    except Exception as e:
        log_feature_fail("ctr_predict", f"AI prediction failed: {e}")
        log_feature_fail("ctr_predict_ai", str(e))
        ai_prediction = services.ctr_predictor.predict_ctr(
            title=request.title,
            thumbnail_description=request.thumbnail_description,
            competitor_titles=request.competitor_titles,
        )

    log_feature_start("ctr_predict_basic", "predict_ctr")
    basic = services.ctr_predictor.predict_ctr(
        title=request.title,
        thumbnail_description=request.thumbnail_description,
        competitor_titles=request.competitor_titles,
    )
    log_feature_end(
        "ctr_predict_basic",
        extra_detail=(
            f"predicted_ctr={basic.get('predicted_ctr')} grade={basic.get('grade')} "
            f"total_score={basic.get('total_score')}"
        ),
    )
    ai_prediction.update(
        {
            "breakdown": basic.get("breakdown", {}),
            "total_score": basic.get("total_score", 0),
            "predicted_ctr": basic.get("predicted_ctr", 0),
            "grade": basic.get("grade", "C"),
            "ctr_range": basic.get("ctr_range", ""),
        }
    )
    log_feature_end(
        "ctr_predict",
        extra_detail=(
            f"predicted_ctr={ai_prediction.get('predicted_ctr')} "
            f"grade={ai_prediction.get('grade')} "
            f"total_score={ai_prediction.get('total_score')}"
        ),
    )
    return {"prediction": ai_prediction}


@router.post("/export/notion")
async def export_notion(
    request: NotionExportRequest,
    user: Annotated[Any, Depends(require_tier("PRO"))],
):
    log_feature_start("export_notion", request.task_id or request.history_id)
    if not request.task_id and not request.history_id:
        log_feature_fail("export_notion", "missing task_id or history_id")
        raise HTTPException(
            status_code=400, detail="task_id 또는 history_id가 필요합니다."
        )

    services = get_services()
    result = None
    if request.task_id:
        try:
            _, result = _get_task_status_and_result(request.task_id)
        except HTTPException:
            result = None

    if result is None and request.history_id:
        record = services.history_service.load_history(request.history_id)
        if record:
            result = record.model_dump()

    if result is None:
        log_feature_fail("export_notion", "Task result not found")
        raise HTTPException(status_code=404, detail="Task result not found")

    product_name = result.get("product_name", "")
    product = get_product_by_name(product_name)
    product_dict = (
        (
            product.model_dump()
            if product and hasattr(product, "model_dump")
            else product.__dict__
        )
        if product
        else {"name": product_name}
    )
    collected = result.get("collected_data") or {}
    strategy = result.get("strategy") or {}
    top_insights = collected.get("top_insights") if isinstance(collected, dict) else []

    export_data = {
        "product": product_dict,
        "analysis": {
            "summary": strategy.get("summary", ""),
            "target_audience": strategy.get("target_audience", {}),
            "hook_suggestions": strategy.get("hook_suggestions", []),
            "competitor_analysis": strategy.get("competitor_analysis", {}),
            "unique_selling_point": strategy.get("unique_selling_point", []),
            "insights": [
                item.get("content", "")
                for item in (top_insights or [])
                if isinstance(item, dict)
            ],
        },
    }

    notion_url = services.export_service.export_notion(
        export_data,
        parent_page_id=request.parent_page_id,
    )
    log_feature_end("export_notion")
    return {"url": notion_url}
