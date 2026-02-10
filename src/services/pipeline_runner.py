# src/services/pipeline_runner.py
import asyncio
import time
from datetime import datetime
from typing import Any

from config.dependencies import get_services
from config.products import get_product_by_name
from config.settings import get_settings
from core.models import PipelineConfig
from core.state import PIPELINE_RESULTS, PIPELINE_STATUS
from schemas.requests import PipelineRequest
from pydantic import ValidationError
from utils.logger import (
    get_logger,
    log_feature_end,
    log_feature_fail,
    log_feature_start,
)

logger = get_logger(__name__)


def _now_iso() -> str:
    return datetime.now().isoformat()


def init_pipeline_status(task_id: str, product_name: str) -> None:
    PIPELINE_STATUS[task_id] = {
        "task_id": task_id,
        "status": "queued",
        "product": product_name,
        "message": "작업 대기 중",
        "process_logs": ["작업 대기 중"],
        "progress": {
            "message": "",
            "percentage": 0,
            "step": "initialized",
        },
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }


def _update_status_impl(task_id: str, fields: dict[str, Any]) -> None:
    status = PIPELINE_STATUS.get(task_id)
    if not status:
        return
    status.update(fields)
    status["updated_at"] = _now_iso()


def _append_process_log_impl(task_id: str, message: str) -> None:
    status = PIPELINE_STATUS.get(task_id)
    if not status:
        return

    msg = (message or "").strip()
    if not msg:
        return

    logs = status.get("process_logs")
    if not isinstance(logs, list):
        logs = []

    last = logs[-1] if logs else None
    if last != msg:
        logs.append(msg)

    # 메모리 보호: 최근 200개까지만 유지
    if len(logs) > 200:
        logs = logs[-200:]

    status["process_logs"] = logs
    status["updated_at"] = _now_iso()


def _store_result_impl(task_id: str, sanitized_result: Any) -> None:
    PIPELINE_RESULTS[task_id] = sanitized_result


def _strip_bytes(value: Any) -> Any:
    if isinstance(value, bytes):
        return None
    if isinstance(value, dict):
        return {k: _strip_bytes(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_strip_bytes(v) for v in value]
    return value


def sanitize_result(result_obj: Any) -> Any:
    if hasattr(result_obj, "model_dump"):
        raw = result_obj.model_dump(
            exclude={
                "generated_content": {"thumbnail_data", "video_bytes"},
            }
        )
    else:
        raw = result_obj.__dict__
    return _strip_bytes(raw)


def summarize_validation_error(exc: ValidationError) -> str:
    """pydantic ValidationError를 운영 로그/상태 메시지에 넣기 좋은 1줄 요약으로 변환."""
    try:
        errors = exc.errors()
    except Exception:
        return "Invalid pipeline config"

    if not errors:
        return "Invalid pipeline config"

    first = errors[0] or {}
    loc = first.get("loc") or []
    msg = str(first.get("msg") or "invalid")
    loc_str = ".".join(str(x) for x in loc) if isinstance(loc, (list, tuple)) else str(loc)
    if loc_str:
        return f"Invalid pipeline config: {loc_str} - {msg}"
    return f"Invalid pipeline config: {msg}"


async def execute_pipeline_task(request: PipelineRequest, task_id: str) -> None:
    """실제 파이프라인 실행 비동기 함수"""
    t0 = time.monotonic()
    log_feature_start("pipeline_run", f"product={request.product_name} task_id={task_id}")
    logger.info(f"Automation Pipeline Start: {request.product_name}")
    _update_status_impl(task_id, {"status": "running", "message": "파이프라인 실행 중"})
    _append_process_log_impl(task_id, "파이프라인 실행 시작")

    loop = asyncio.get_running_loop()
    persist_task: asyncio.Task[None] | None = None

    try:
        services = get_services()
        pipeline_service = services.pipeline_service
        pipeline_task_service = getattr(services, "pipeline_task_service", None)

        async def _persist_status_loop() -> None:
            # Cloud Run 다중 인스턴스에서 상태가 인메모리에만 있으면 404/불안정이 발생한다.
            # 주기적으로 현재 상태를 DB에 스냅샷으로 저장해 어디로 라우팅되든 조회 가능하게 만든다.
            if pipeline_task_service is None:
                return

            while True:
                status = PIPELINE_STATUS.get(task_id)
                if status:
                    await pipeline_task_service.upsert_status(status)

                if not status or status.get("status") in {"success", "failed"}:
                    break

                await asyncio.sleep(2)

        if pipeline_task_service is not None:
            # 시작/진행 중 상태 저장을 백그라운드로 유지
            persist_task = asyncio.create_task(_persist_status_loop())
            # 초기 상태는 즉시 1회 저장(best-effort)
            await pipeline_task_service.upsert_status(PIPELINE_STATUS.get(task_id) or {})

        product_data = get_product_by_name(request.product_name)
        if not product_data:
            raise ValueError(f"Product '{request.product_name}' not found")

        # dict 변환
        if hasattr(product_data, "model_dump"):
            product_dict = product_data.model_dump()
        else:
            product_dict = product_data.__dict__

        resolved_thumbnail_count = request.thumbnail_count
        if resolved_thumbnail_count is None and request.thumbnail_styles:
            resolved_thumbnail_count = min(len(request.thumbnail_styles), 5)

        try:
            config = PipelineConfig(
                youtube_count=request.youtube_count,
                naver_count=request.naver_count,
                include_comments=request.include_comments,
                generate_social=request.generate_social,
                generate_video=request.generate_video,
                generate_thumbnail=request.generate_thumbnails,
                generate_multi_thumbnails=request.generate_thumbnails,
                thumbnail_count=(
                    resolved_thumbnail_count
                    if resolved_thumbnail_count is not None
                    else (3 if request.generate_thumbnails else 1)
                ),
                thumbnail_styles=request.thumbnail_styles,
                video_dual_phase_beta=False,
                upload_to_gcs=True,
            )
        except ValidationError as ve:
            # Cloud Logging에 원인(필드/메시지)이 안 남으면 원인 추적이 불가능해진다.
            # 민감정보는 포함되지 않으므로 errors()를 안전하게 남긴다.
            summary = summarize_validation_error(ve)
            log_feature_fail("pipeline_run", summary)
            logger.error("PipelineConfig validation failed: %s", summary)
            try:
                logger.error("PipelineConfig validation errors: %s", ve.errors())
            except Exception:
                pass

            _update_status_impl(
                task_id,
                {
                    "status": "failed",
                    "message": summary,
                },
            )
            _append_process_log_impl(task_id, summary)
            if pipeline_task_service is not None:
                await pipeline_task_service.upsert_status(
                    PIPELINE_STATUS.get(task_id) or {}
                )
            return

        def progress_callback(progress: Any) -> None:
            msg = progress.message
            pct = progress.percentage
            step = getattr(progress.current_step, "value", progress.current_step)

            logger.info(f"[{request.product_name}] {msg}")

            fields = {
                "progress": {
                    "message": msg,
                    "percentage": pct,
                    "step": step,
                }
            }
            loop.call_soon_threadsafe(_update_status_impl, task_id, fields)
            loop.call_soon_threadsafe(_append_process_log_impl, task_id, msg)

        # 파이프라인 실행
        result = await pipeline_service.execute(
            product=product_dict,
            config=config,
            progress_callback=progress_callback,
        )

        sanitized = sanitize_result(result)
        _store_result_impl(task_id, sanitized)
        if pipeline_task_service is not None and isinstance(sanitized, dict):
            await pipeline_task_service.upsert_result(task_id, sanitized)

        if result.success:
            log_feature_end(
                "pipeline_run",
                duration_sec=time.monotonic() - t0,
                extra_detail=request.product_name,
            )
            logger.info(f"Automation Pipeline Success: {request.product_name}")
            _update_status_impl(
                task_id, {"status": "success", "message": "파이프라인 완료"}
            )
            _append_process_log_impl(task_id, "파이프라인 완료")
            if pipeline_task_service is not None:
                await pipeline_task_service.upsert_status(
                    PIPELINE_STATUS.get(task_id) or {}
                )

            # 노션 자동 포스팅 실행
            if request.export_to_notion:
                try:
                    logger.info(f"Exporting to Notion: {request.product_name}")
                    if result.collected_data:
                        insights = [
                            i.get("content", "")
                            for i in result.collected_data.top_insights
                        ]
                    else:
                        insights = []

                    gen = result.generated_content
                    generated_content_payload: dict[str, Any] = {}
                    if gen is not None:
                        generated_content_payload = {
                            "thumbnail_url": getattr(gen, "thumbnail_url", None),
                            "video_url": getattr(gen, "video_url", None),
                            "video_path": getattr(gen, "video_path", None),
                            # Notion으로 보낼 때는 bytes는 절대 포함하지 않는다.
                            "multi_thumbnails": [
                                {
                                    k: v
                                    for k, v in (item or {}).items()
                                    if k not in {"image", "image_bytes"}
                                }
                                for item in (getattr(gen, "multi_thumbnails", None) or [])
                                if isinstance(item, dict)
                            ],
                        }

                    metrics_payload: dict[str, Any] = {}
                    if result.collected_data and result.collected_data.top_insights:
                        metrics_payload["top_insights"] = result.collected_data.top_insights
                    if result.pipeline_metrics is not None:
                        try:
                            metrics_payload["pipeline_metrics"] = result.pipeline_metrics.model_dump()
                        except Exception:
                            metrics_payload["pipeline_metrics"] = {}

                    export_data = {
                        "product": product_dict,
                        "meta": {
                            "task_id": task_id,
                            "executed_at": (
                                result.executed_at.isoformat()
                                if getattr(result, "executed_at", None)
                                else _now_iso()
                            ),
                            "duration_seconds": float(getattr(result, "duration_seconds", 0.0) or 0.0),
                            "ai_stages_used": getattr(result, "ai_stages_used", []) or [],
                            "upload_status": getattr(getattr(result, "upload_status", None), "value", None)
                            or str(getattr(result, "upload_status", "")),
                            "upload_errors": getattr(result, "upload_errors", []) or [],
                        },
                        "analysis": {
                            "summary": result.strategy.get("summary", ""),
                            "target_audience": result.strategy.get(
                                "target_audience", {}
                            ),
                            "hook_suggestions": result.strategy.get(
                                "hook_suggestions", []
                            ),
                            "competitor_analysis": result.strategy.get(
                                "competitor_analysis", {}
                            ),
                            "unique_selling_point": result.strategy.get(
                                "unique_selling_point", []
                            ),
                            "insights": insights,
                        },
                        "metrics": metrics_payload,
                        "generated_content": generated_content_payload,
                        "selected_outputs": getattr(result, "selected_outputs", None),
                    }
                    notion_url = services.export_service.export_notion(export_data)
                    logger.info(f"Notion Export Success: {notion_url}")
                except Exception as ne:
                    logger.error(f"Notion Export Failed: {ne!s}")
        else:
            log_feature_fail("pipeline_run", result.error_message or "unknown")
            logger.error(
                f"Automation Pipeline Failed: {request.product_name} - {result.error_message}"
            )
            _update_status_impl(
                task_id,
                {
                    "status": "failed",
                    "message": result.error_message or "파이프라인 실패",
                },
            )
            _append_process_log_impl(
                task_id, result.error_message or "파이프라인 실패"
            )
            if pipeline_task_service is not None:
                await pipeline_task_service.upsert_status(
                    PIPELINE_STATUS.get(task_id) or {}
                )

    except Exception as e:
        log_feature_fail("pipeline_run", str(e))
        logger.exception(f"Automation Pipeline Exception: {e!s}")
        settings = get_settings()
        debug_message = f"Pipeline exception: {e!s}"
        _update_status_impl(
            task_id,
            {
                "status": "failed",
                "message": debug_message
                if settings.app.debug
                else "Pipeline exception occurred",
            },
        )
        _append_process_log_impl(task_id, debug_message)
        try:
            services = get_services()
            pipeline_task_service = getattr(services, "pipeline_task_service", None)
            if pipeline_task_service is not None:
                await pipeline_task_service.upsert_status(
                    PIPELINE_STATUS.get(task_id) or {}
                )
        except Exception:
            # best-effort: DB가 없거나 깨져도 파이프라인 자체 예외 처리 흐름은 유지
            pass
    finally:
        if persist_task is not None:
            persist_task.cancel()
            try:
                await persist_task
            except asyncio.CancelledError:
                pass
