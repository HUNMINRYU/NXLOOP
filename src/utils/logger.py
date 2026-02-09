"""
Logging utilities for Nexloop.
"""

import contextlib
import logging
import sys
from collections.abc import Callable
from typing import ClassVar


class ColoredFormatter(logging.Formatter):
    """Optional ANSI color formatter (ASCII-only output)."""

    COLORS: ClassVar[dict[str, str]] = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET: ClassVar[str] = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        record.color = color
        record.reset = self.RESET
        return super().format(record)


_app_logger: logging.Logger | None = None
_log_callbacks: list[Callable[[str], None]] = []


class CallbackHandler(logging.Handler):
    """Emit formatted logs to registered callbacks (for UI/debug)."""

    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
        self.formatter = ColoredFormatter(
            "[%(asctime)s] %(levelname)s - %(message)s",
            datefmt="%H:%M:%S",
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            for callback in _log_callbacks:
                with contextlib.suppress(Exception):
                    callback(msg)
        except Exception:
            self.handleError(record)


def add_log_callback(callback: Callable[[str], None]) -> None:
    if callback not in _log_callbacks:
        _log_callbacks.append(callback)


def clear_log_callbacks() -> None:
    _log_callbacks.clear()


def setup_logger(name: str = "nexloop", level: int = logging.DEBUG) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    formatter = ColoredFormatter(
        "[%(asctime)s] %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(formatter)

    callback_handler = CallbackHandler(logging.INFO)
    callback_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(callback_handler)
    logger.propagate = False

    return logger


def _stream_is_closed(stream: object) -> bool:
    if stream is None:
        return True
    try:
        if getattr(stream, "closed", False):
            return True
    except Exception:
        return True
    try:
        writable = getattr(stream, "writable", None)
        if callable(writable) and not writable():
            return True
    except Exception:
        return True
    return False


def _has_closed_stream_handler(logger: logging.Logger) -> bool:
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and _stream_is_closed(
            getattr(handler, "stream", None)
        ):
            return True
    return False


def get_logger(name: str = "nexloop") -> logging.Logger:
    global _app_logger
    if _app_logger is None:
        _app_logger = setup_logger(name)
        return _app_logger
    if not _app_logger.handlers or _has_closed_stream_handler(_app_logger):
        _app_logger = setup_logger(name)
    return _app_logger


def log_section(title: str) -> None:
    get_logger().info("\n" + "=" * 50)
    get_logger().info(f"== {title} ==")
    get_logger().info("=" * 50)


def log_app_start() -> None:
    log_section("App start")


def log_app_ready() -> None:
    log_success("App ready")


def log_step(step_name: str, status: str = "start", details: str = "") -> None:
    icon = "👉" if status == "start" else "✅" if status == "complete" else "👣"
    msg = f"[STEP] {icon} {step_name} - {status}"
    if details:
        msg += f" ({details})"
    get_logger().info(msg)


# ============================================================
# [FEATURE] 기능 단위 로깅 — 무슨 기능이 실행 중인지 항상 파악
# ============================================================


def log_feature_start(feature: str, detail: str = "") -> None:
    """기능 실행 시작. 로그 검색 시 [FEATURE] 로 필터링 가능."""
    msg = f"[FEATURE] ▶ {feature} 시작"
    if detail:
        msg += f" | {detail}"
    get_logger().info(msg, extra={"feature": feature, "event": "start"})


def log_feature_end(feature: str, duration_sec: float = 0, extra_detail: str = "") -> None:
    """기능 실행 완료."""
    msg = f"[FEATURE] ■ {feature} 완료"
    if duration_sec > 0:
        msg += f" | {duration_sec:.2f}s"
    if extra_detail:
        msg += f" | {extra_detail}"
    get_logger().info(msg, extra={"feature": feature, "event": "end", "duration_sec": duration_sec})


def log_feature_fail(feature: str, error: str = "") -> None:
    """기능 실행 실패."""
    msg = f"[FEATURE] ✖ {feature} 실패"
    if error:
        msg += f" | {error[:200]}"
    get_logger().error(msg, extra={"feature": feature, "event": "fail"})


def log_info(message: str) -> None:
    get_logger().info(message)


def log_debug(message: str) -> None:
    get_logger().debug(message)


def log_warning(message: str) -> None:
    get_logger().warning(message)


def log_error(message: str) -> None:
    get_logger().error(message)


def log_success(message: str) -> None:
    get_logger().info(f"SUCCESS: {message}")


def log_llm_request(
    usage: str,
    details: str = "",
    model: str = "",
    prompt_preview: str = "",
    max_preview_len: int = 150,
) -> None:
    """LLM 요청 로그 (상세 버전)"""
    get_logger().info("")
    get_logger().info("===== 🤖 LLM 요청 =====")
    get_logger().info(f"   📌 용도: {usage}")
    if model:
        get_logger().info(f"   🧠 모델: {model}")
    if details:
        get_logger().info(f"   📋 상세: {details}")
    if prompt_preview:
        preview = prompt_preview[:max_preview_len]
        if len(prompt_preview) > max_preview_len:
            preview += "..."
        preview = preview.replace("\n", " ").strip()
        get_logger().info(f"   📝 프롬프트: {preview}")


def log_llm_response(
    usage: str,
    details: str = "",
    response_preview: str = "",
    token_count: int = 0,
    duration_ms: float = 0,
    max_preview_len: int = 150,
) -> None:
    """LLM 응답 로그 (상세 버전)"""
    get_logger().info("✅ LLM 응답 수신: " + usage)
    if details:
        get_logger().info(f"   📊 결과: {details}")
    if response_preview:
        preview = response_preview[:max_preview_len]
        if len(response_preview) > max_preview_len:
            preview += "..."
        preview = preview.replace("\n", " ").strip()
        get_logger().info(f"   📤 응답: {preview}")
    if token_count > 0:
        get_logger().info(f"   🔢 토큰 사용: {token_count}")
    if duration_ms > 0:
        get_logger().info(f"   ⏱️ 소요: {duration_ms:.0f}ms")


def log_llm_fail(usage: str, error: str = "", model: str = "") -> None:
    """LLM 실패 로그 (상세 버전)"""
    get_logger().error("===== ❌ LLM 요청 실패 =====")
    get_logger().error(f"   📌 용도: {usage}")
    if model:
        get_logger().error(f"   🧠 모델: {model}")
    if error:
        error_short = str(error)[:200]
        get_logger().error(f"   ⚠️ 오류: {error_short}")


def log_api_call(api_name: str, endpoint: str = "", status: str = "sent") -> None:
    get_logger().info(f"[API] {api_name} {endpoint} - {status}")


def log_api_start(api_name: str, details: str = "") -> None:
    get_logger().info(f"[API] 🚀 {api_name} request start")
    if details:
        get_logger().info(f"      📋 Info: {details}")


def log_api_end(api_name: str, duration: float = 0, items: int = 0) -> None:
    msg = f"[API] ✅ {api_name} response end"
    if duration > 0:
        msg += f" ({duration:.2f}s)"
    if items > 0:
        msg += f" - {items} items"
    get_logger().info(msg)


def log_process(task: str, current: int, total: int) -> None:
    percent = int((current / total) * 100) if total else 0
    bar_len = 10
    filled = int(percent / 100 * bar_len)
    bar = "#" * filled + "-" * (bar_len - filled)
    get_logger().info(f"[PROCESS] ⏳ {task}: [{bar}] {percent}%")


def log_timing(operation: str, duration_ms: float) -> None:
    get_logger().info(f"[TIMING] ⏱️ {operation}: {duration_ms:.2f}ms")


def log_tab_load(tab_name: str) -> None:
    get_logger().info(f"[TAB] {tab_name} loaded")


def log_user_action(action: str, details: str = "") -> None:
    get_logger().info(f"[USER] {action} {details}")


def log_data(label: str, value: object = None, source: str = "") -> None:
    if source:
        get_logger().info(f"[DATA] {source} {label}: {value}")
    else:
        get_logger().info(f"[DATA] {label}: {value}")


def log_function(name: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            log_debug(f"[FUNC] {name}")
            return func(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================
# 🇰🇷 한글 상세 로깅 함수 (Input/Output 추적용)
# ============================================================


def log_stage_start(stage_name: str, description: str = "") -> None:
    """단계 시작 로그 (한글)"""
    get_logger().info("")
    get_logger().info("=" * 50)
    get_logger().info(f"🚀 [{stage_name}] 시작")
    if description:
        get_logger().info(f"   [i] {description}")


def log_stage_end(
    stage_name: str, result_summary: str = "", duration_ms: float = 0
) -> None:
    """단계 완료 로그 (한글)"""
    get_logger().info(f"✅ [{stage_name}] 완료")
    if result_summary:
        get_logger().info(f"   📊 결과: {result_summary}")
    if duration_ms > 0:
        get_logger().info(f"   ⏱️  소요 시간: {duration_ms:.2f}ms")
    get_logger().info("")


def log_stage_fail(stage_name: str, error_msg: str = "") -> None:
    """단계 실패 로그 (한글)"""
    get_logger().error(f"❌ [{stage_name}] 실패")
    if error_msg:
        get_logger().error(f"   ⚠️  오류: {error_msg}")


def log_input_data(label: str, data: object, max_length: int = 200) -> None:
    """입력 데이터 로그 (한글)"""
    data_str = str(data)
    if len(data_str) > max_length:
        data_str = data_str[:max_length] + "... (생략)"
    get_logger().info(f"   📥 [입력] {label}: {data_str}")


def log_output_data(label: str, data: object, max_length: int = 200) -> None:
    """출력 데이터 로그 (한글)"""
    data_str = str(data)
    if len(data_str) > max_length:
        data_str = data_str[:max_length] + "... (생략)"
    get_logger().info(f"   📤 [출력] {label}: {data_str}")


def log_prompt_start(prompt_name: str, context: str = "") -> None:
    """프롬프트 호출 시작 로그"""
    get_logger().info(f"   🤖 [프롬프트] {prompt_name} 호출 시작")
    if context:
        get_logger().info(
            f"      📋 컨텍스트: {context[:150]}..."
            if len(context) > 150
            else f"      📋 컨텍스트: {context}"
        )


def log_prompt_end(prompt_name: str, output_preview: str = "") -> None:
    """프롬프트 호출 완료 로그"""
    get_logger().info(f"   ✨ [프롬프트] {prompt_name} 응답 수신")
    if output_preview:
        preview = (
            output_preview[:150] + "..."
            if len(output_preview) > 150
            else output_preview
        )
        get_logger().info(f"      📝 응답 미리보기: {preview}")


def log_api_request(
    service_name: str, endpoint: str, params: dict | None = None
) -> None:
    """API 요청 로그 (상세)"""
    get_logger().info(f"   🌐 [API 요청] {service_name} → {endpoint}")
    if params:
        params_str = (
            str(params)[:100] + "..." if len(str(params)) > 100 else str(params)
        )
        get_logger().info(f"      📦 파라미터: {params_str}")


def log_api_response(service_name: str, status: str, data_summary: str = "") -> None:
    """API 응답 로그 (상세)"""
    get_logger().info(f"   📬 [API 응답] {service_name}: {status}")
    if data_summary:
        get_logger().info(f"      📊 데이터 요약: {data_summary}")


def log_llm_input(
    model_name: str, prompt_preview: str, token_estimate: int = 0
) -> None:
    """LLM 입력 로그 (상세)"""
    get_logger().info(f"   🧠 [LLM 입력] 모델: {model_name}")
    preview = (
        prompt_preview[:200] + "..." if len(prompt_preview) > 200 else prompt_preview
    )
    get_logger().info(f"      📝 프롬프트: {preview}")
    if token_estimate > 0:
        get_logger().info(f"      🔢 예상 토큰: ~{token_estimate}")


def log_llm_output(model_name: str, response_preview: str, token_used: int = 0) -> None:
    """LLM 출력 로그 (상세)"""
    get_logger().info(f"   💡 [LLM 출력] 모델: {model_name}")
    preview = (
        response_preview[:200] + "..."
        if len(response_preview) > 200
        else response_preview
    )
    get_logger().info(f"      📤 응답: {preview}")
    if token_used > 0:
        get_logger().info(f"      🔢 사용 토큰: {token_used}")


def log_pipeline_progress(
    step_number: int, total_steps: int, step_name: str, status: str = "진행중"
) -> None:
    """파이프라인 진행 상황 로그"""
    percent = int((step_number / total_steps) * 100)
    get_logger().info(f"   📊 진행: {percent}% - {step_name}: {status}")


def log_service_call(
    service_name: str, method_name: str, args_summary: str = ""
) -> None:
    """서비스 호출 로그"""
    get_logger().info(f"   ⚙️  [서비스 호출] {service_name}.{method_name}()")
    if args_summary:
        get_logger().info(f"      📦 인자: {args_summary}")


def log_service_result(
    service_name: str, method_name: str, result_summary: str = ""
) -> None:
    """서비스 결과 로그"""
    get_logger().info(f"   ✔️  [서비스 완료] {service_name}.{method_name}()")
    if result_summary:
        get_logger().info(f"      📤 결과: {result_summary}")


def log_json_data(label: str, json_obj: dict, keys_to_show: list | None = None) -> None:
    """JSON 데이터 로그 (선택적 키만 표시)"""
    if keys_to_show:
        filtered = {k: json_obj.get(k, "(없음)") for k in keys_to_show if k in json_obj}
        get_logger().info(f"   📋 [데이터] {label}: {filtered}")
    else:
        preview = (
            str(json_obj)[:200] + "..." if len(str(json_obj)) > 200 else str(json_obj)
        )
        get_logger().info(f"   📋 [데이터] {label}: {preview}")


def log_product_context(product: dict) -> None:
    """제품 컨텍스트 로그"""
    name = product.get("name", "N/A")
    category = product.get("category", "N/A")
    desc_preview = (product.get("description") or "")[:50]
    get_logger().info(f"   🛒 [제품 정보] 이름: {name}, 카테고리: {category}")
    if desc_preview:
        get_logger().info(f"      📝 설명: {desc_preview}...")


def log_separator(style: str = "single") -> None:
    """구분선 로그"""
    if style == "double":
        get_logger().info("=" * 60)
    else:
        get_logger().info("=" * 50)


def log_summary_box(title: str, items: list) -> None:
    """요약 로그"""
    get_logger().info("")
    get_logger().info("=" * 50)
    get_logger().info(f"📊 {title}")
    get_logger().info("=" * 50)
    for item in items[:10]:  # 최대 10개만 표시
        get_logger().info(f"  • {item}")
    if len(items) > 10:
        get_logger().info(f"  ... 외 {len(items) - 10}개 항목")
    get_logger().info("=" * 50)
