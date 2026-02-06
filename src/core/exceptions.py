"""
커스텀 예외 클래스 및 에러 핸들링 유틸리티
사용자 친화적인 에러 메시지를 제공합니다.
"""

from enum import Enum
from typing import Any


class ErrorCode(Enum):
    """에러 코드 정의"""

    # 인증/설정 관련
    AUTH_FAILED = "AUTH_001"
    CONFIG_MISSING = "CONFIG_001"
    API_KEY_INVALID = "API_001"

    # 네트워크/API 관련
    NETWORK_ERROR = "NET_001"
    API_RATE_LIMIT = "API_002"
    API_TIMEOUT = "API_003"
    API_RESPONSE_ERROR = "API_004"

    # 데이터 관련
    DATA_NOT_FOUND = "DATA_001"
    DATA_INVALID = "DATA_002"
    DATA_PARSE_ERROR = "DATA_003"

    # 서비스 관련
    SERVICE_UNAVAILABLE = "SVC_001"
    GENERATION_FAILED = "SVC_002"
    EXPORT_FAILED = "SVC_003"

    # 스케줄러 관련
    SCHEDULER_NOT_FOUND = "SCH_001"
    SCHEDULER_DUPLICATE = "SCH_002"
    SCHEDULER_AUTH = "SCH_003"
    SCHEDULER_QUOTA = "SCH_004"
    SCHEDULER_CONFLICT = "SCH_005"
    SCHEDULER_INVALID_CRON = "SCH_006"

    # 일반
    UNKNOWN_ERROR = "ERR_999"


class ErrorSeverity(Enum):
    """에러 심각도 및 재시도 가능 여부"""

    RETRYABLE_TRANSIENT = "retryable_transient"
    RETRYABLE_PERMANENT = "retryable_permanent"
    PERMANENT = "permanent"


# 사용자 친화적 에러 메시지 매핑
USER_FRIENDLY_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.AUTH_FAILED: "인증에 실패했습니다. API 키를 확인해주세요.",
    ErrorCode.CONFIG_MISSING: "설정 파일(.env)이 누락되었습니다. 설정을 확인해주세요.",
    ErrorCode.API_KEY_INVALID: "API 키가 유효하지 않습니다. 올바른 키를 입력해주세요.",
    ErrorCode.NETWORK_ERROR: "네트워크 연결에 문제가 있습니다. 인터넷 연결을 확인해주세요.",
    ErrorCode.API_RATE_LIMIT: "API 호출 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
    ErrorCode.API_TIMEOUT: "서버 응답이 너무 오래 걸립니다. 나중에 다시 시도해주세요.",
    ErrorCode.API_RESPONSE_ERROR: "서버에서 예상치 못한 응답을 받았습니다.",
    ErrorCode.DATA_NOT_FOUND: "요청한 데이터를 찾을 수 없습니다.",
    ErrorCode.DATA_INVALID: "입력 데이터가 올바르지 않습니다. 다시 확인해주세요.",
    ErrorCode.DATA_PARSE_ERROR: "데이터 처리 중 오류가 발생했습니다.",
    ErrorCode.SERVICE_UNAVAILABLE: "서비스가 일시적으로 사용 불가능합니다. 잠시 후 다시 시도해주세요.",
    ErrorCode.GENERATION_FAILED: "콘텐츠 생성에 실패했습니다. 다시 시도해주세요.",
    ErrorCode.EXPORT_FAILED: "내보내기에 실패했습니다. 설정을 확인해주세요.",
    ErrorCode.UNKNOWN_ERROR: "알 수 없는 오류가 발생했습니다. 문제가 지속되면 관리자에게 문의해주세요.",
    ErrorCode.SCHEDULER_NOT_FOUND: "스케줄을 찾을 수 없습니다.",
    ErrorCode.SCHEDULER_DUPLICATE: "동일한 스케줄이 이미 존재합니다.",
    ErrorCode.SCHEDULER_AUTH: "Cloud Scheduler 인증에 실패했습니다.",
    ErrorCode.SCHEDULER_QUOTA: "Cloud Scheduler 할당량을 초과했습니다.",
    ErrorCode.SCHEDULER_CONFLICT: "스케줄이 다른 사용자에 의해 수정되었습니다. 새로고침 후 다시 시도해주세요.",
    ErrorCode.SCHEDULER_INVALID_CRON: "유효하지 않은 크론 표현식입니다.",
}

# 해결 방법 힌트 매핑
SOLUTION_HINTS: dict[ErrorCode, str] = {
    ErrorCode.AUTH_FAILED: "💡 .env 파일에서 API 키가 올바르게 설정되어 있는지 확인하세요.",
    ErrorCode.CONFIG_MISSING: "💡 프로젝트 루트에 .env 파일이 있는지 확인하세요.",
    ErrorCode.API_KEY_INVALID: "💡 Google Cloud Console 또는 해당 서비스에서 새 API 키를 발급받으세요.",
    ErrorCode.NETWORK_ERROR: "💡 VPN을 사용 중이라면 끄고 다시 시도해보세요.",
    ErrorCode.API_RATE_LIMIT: "💡 1-2분 후에 다시 시도하거나, 유료 플랜으로 업그레이드하세요.",
    ErrorCode.API_TIMEOUT: "💡 검색어를 더 간단하게 변경하거나 나중에 다시 시도하세요.",
    ErrorCode.DATA_NOT_FOUND: "💡 먼저 YouTube/Naver 탭에서 데이터를 수집해주세요.",
    ErrorCode.GENERATION_FAILED: "💡 입력 텍스트를 수정하거나 다른 옵션을 선택해보세요.",
    ErrorCode.EXPORT_FAILED: "💡 Notion API 키와 Database ID가 올바른지 확인하세요.",
    ErrorCode.SCHEDULER_AUTH: "💡 서비스 계정 권한과 SCHEDULER_SERVICE_ACCOUNT 설정을 확인하세요.",
    ErrorCode.SCHEDULER_QUOTA: "💡 GCP 콘솔에서 Cloud Scheduler 할당량을 확인하세요.",
    ErrorCode.SCHEDULER_CONFLICT: "💡 페이지를 새로고침하고 다시 시도하세요.",
}


class NexloopError(Exception):
    """넥스루프 스튜디오 기본 예외 클래스"""

    def __init__(
        self,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        message: str | None = None,
        original_error: Exception | None = None,
        details: dict[str, Any] | None = None,
        severity: ErrorSeverity = ErrorSeverity.PERMANENT,
        retry_after: float | None = None,
    ):
        self.code = code
        self.original_error = original_error
        self.details = details or {}
        self.severity = severity
        self.retry_after = retry_after

        # 사용자 친화적 메시지 사용 (커스텀 메시지가 없으면)
        self.user_message = message or USER_FRIENDLY_MESSAGES.get(
            code, "오류가 발생했습니다."
        )
        self.hint = SOLUTION_HINTS.get(code, "")

        super().__init__(self.user_message)

    def __str__(self) -> str:
        return self.user_message

    def get_full_message(self) -> str:
        """힌트를 포함한 전체 메시지 반환"""
        if self.hint:
            return f"{self.user_message}\n\n{self.hint}"
        return self.user_message

    def get_debug_info(self) -> str:
        """디버그용 상세 정보 반환"""
        info = f"[{self.code.value}] {self.user_message}"
        if self.original_error:
            info += f"\n원본 에러: {type(self.original_error).__name__}: {self.original_error}"
        if self.details:
            info += f"\n상세: {self.details}"
        return info

    def is_retryable(self) -> bool:
        """재시도 가능 여부"""
        return self.severity != ErrorSeverity.PERMANENT

    def get_retry_delay(self) -> float | None:
        """재시도 대기 시간"""
        return self.retry_after


class APIError(NexloopError):
    """API 관련 에러"""

    def __init__(
        self, service_name: str, original_error: Exception | None = None, **kwargs
    ):
        self.service_name = service_name
        super().__init__(
            code=kwargs.get("code", ErrorCode.API_RESPONSE_ERROR),
            original_error=original_error,
            details={"service": service_name, **kwargs.get("details", {})},
        )


class YouTubeAPIError(APIError):
    """YouTube API 관련 에러"""

    def __init__(
        self,
        message: str = "YouTube API 호출에 실패했습니다.",
        details: dict | None = None,
        **kwargs,
    ):
        super().__init__(service_name="YouTube", **kwargs)
        self.user_message = message
        if details:
            self.details.update(details)


class NaverAPIError(APIError):
    """Naver API 관련 에러"""

    def __init__(
        self,
        message: str = "Naver API 호출에 실패했습니다.",
        details: dict | None = None,
        **kwargs,
    ):
        super().__init__(service_name="Naver", **kwargs)
        self.user_message = message
        if details:
            self.details.update(details)


class AuthenticationError(NexloopError):
    """인증 관련 에러"""

    def __init__(self, service_name: str = "Unknown", **kwargs):
        super().__init__(
            code=ErrorCode.AUTH_FAILED,
            message=f"{service_name} 인증에 실패했습니다.",
            **kwargs,
        )


class DataError(NexloopError):
    """데이터 관련 에러"""

    pass


class DataCollectionError(DataError):
    """데이터 수집 관련 에러"""

    def __init__(self, message: str = "데이터 수집에 실패했습니다.", **kwargs):
        super().__init__(
            code=ErrorCode.DATA_NOT_FOUND,
            message=message,
            **kwargs,
        )


class GeminiAPIError(APIError):
    """Gemini API 관련 에러"""

    def __init__(self, message: str = "Gemini API 호출에 실패했습니다.", **kwargs):
        super().__init__(
            service_name="Gemini",
            code=ErrorCode.API_RESPONSE_ERROR,
            **kwargs,
        )
        self.user_message = message


class GenerationError(NexloopError):
    """콘텐츠 생성 관련 에러"""

    def __init__(self, content_type: str = "콘텐츠", **kwargs):
        super().__init__(
            code=ErrorCode.GENERATION_FAILED,
            message=f"{content_type} 생성에 실패했습니다. 다시 시도해주세요.",
            **kwargs,
        )


class StrategyGenerationError(GenerationError):
    """마케팅 전략 생성 관련 에러"""

    def __init__(self, message: str = "마케팅 전략 생성에 실패했습니다.", **kwargs):
        super().__init__(content_type="마케팅 전략", **kwargs)
        self.user_message = message


class ExportError(NexloopError):
    """내보내기 관련 에러"""

    def __init__(self, export_type: str = "데이터", **kwargs):
        super().__init__(
            code=ErrorCode.EXPORT_FAILED,
            message=f"{export_type} 내보내기에 실패했습니다.",
            **kwargs,
        )


class VeoAPIError(APIError):
    """Veo API 관련 에러"""

    def __init__(self, message: str = "Veo API 호출에 실패했습니다.", **kwargs):
        super().__init__(service_name="Veo", **kwargs)
        self.user_message = message


class VideoGenerationError(GenerationError):
    """비디오 생성 관련 에러"""

    def __init__(self, message: str = "비디오 생성에 실패했습니다.", **kwargs):
        super().__init__(content_type="비디오", **kwargs)
        self.user_message = message


class ThumbnailGenerationError(GenerationError):
    """썸네일 생성 관련 에러"""

    def __init__(self, message: str = "썸네일 생성에 실패했습니다.", **kwargs):
        super().__init__(content_type="썸네일", **kwargs)
        self.user_message = message


class PipelineError(NexloopError):
    """파이프라인 실행 관련 에러"""

    def __init__(self, message: str = "파이프라인 실행에 실패했습니다.", **kwargs):
        super().__init__(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message=message,
            **kwargs,
        )


class StorageError(NexloopError):
    """스토리지 관련 에러"""

    def __init__(self, message: str = "스토리지 작업에 실패했습니다.", **kwargs):
        super().__init__(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message=message,
            **kwargs,
        )


class GCSUploadError(StorageError):
    """GCS 업로드 에러"""

    def __init__(self, message: str = "GCS 업로드에 실패했습니다.", **kwargs):
        super().__init__(message=message, **kwargs)


class GCSDownloadError(StorageError):
    """GCS 다운로드 에러"""

    def __init__(self, message: str = "GCS 다운로드에 실패했습니다.", **kwargs):
        super().__init__(message=message, **kwargs)


class SchedulerError(NexloopError):
    """Cloud Scheduler 기본 예외"""

    def __init__(self, message: str = "스케줄러 작업에 실패했습니다.", **kwargs):
        super().__init__(
            code=kwargs.pop("code", ErrorCode.SERVICE_UNAVAILABLE),
            message=message,
            **kwargs,
        )


class ScheduleNotFoundError(SchedulerError):
    """스케줄을 찾을 수 없음"""

    def __init__(self, schedule_id: int | str = "", **kwargs):
        super().__init__(
            code=ErrorCode.SCHEDULER_NOT_FOUND,
            message=f"스케줄을 찾을 수 없습니다: {schedule_id}" if schedule_id else "스케줄을 찾을 수 없습니다.",
            severity=ErrorSeverity.PERMANENT,
            **kwargs,
        )


class ScheduleDuplicateError(SchedulerError):
    """중복 스케줄 Job"""

    def __init__(self, job_id: str = "", **kwargs):
        super().__init__(
            code=ErrorCode.SCHEDULER_DUPLICATE,
            message=f"동일한 스케줄 Job이 이미 존재합니다: {job_id}" if job_id else "동일한 스케줄이 이미 존재합니다.",
            severity=ErrorSeverity.PERMANENT,
            **kwargs,
        )


class SchedulerAuthError(SchedulerError):
    """Cloud Scheduler 인증 실패"""

    def __init__(self, **kwargs):
        super().__init__(
            code=ErrorCode.SCHEDULER_AUTH,
            message="Cloud Scheduler 인증에 실패했습니다. 서비스 계정 권한을 확인해주세요.",
            severity=ErrorSeverity.PERMANENT,
            **kwargs,
        )


class SchedulerQuotaError(SchedulerError):
    """Cloud Scheduler 할당량 초과"""

    def __init__(self, **kwargs):
        super().__init__(
            code=ErrorCode.SCHEDULER_QUOTA,
            message="Cloud Scheduler 할당량을 초과했습니다. 잠시 후 다시 시도해주세요.",
            severity=ErrorSeverity.RETRYABLE_TRANSIENT,
            retry_after=60.0,
            **kwargs,
        )


class ScheduleConflictError(SchedulerError):
    """동시 수정 충돌 (Optimistic Locking)"""

    def __init__(self, schedule_id: int | str = "", **kwargs):
        super().__init__(
            code=ErrorCode.SCHEDULER_CONFLICT,
            message="스케줄이 다른 사용자에 의해 수정되었습니다. 새로고침 후 다시 시도해주세요.",
            severity=ErrorSeverity.PERMANENT,
            **kwargs,
        )


class InvalidCronError(SchedulerError):
    """유효하지 않은 크론 표현식"""

    def __init__(self, cron: str = "", **kwargs):
        super().__init__(
            code=ErrorCode.SCHEDULER_INVALID_CRON,
            message=f"유효하지 않은 크론 표현식입니다: {cron}" if cron else "유효하지 않은 크론 표현식입니다.",
            severity=ErrorSeverity.PERMANENT,
            **kwargs,
        )


def classify_error(error: Exception) -> NexloopError:
    """
    일반 예외를 NexloopError로 변환합니다.
    에러 메시지를 분석하여 적절한 에러 코드를 할당합니다.
    """
    error_str = str(error).lower()

    # 네트워크 관련 키워드
    if any(kw in error_str for kw in ["connection", "timeout", "network", "연결"]):
        return NexloopError(
            code=ErrorCode.NETWORK_ERROR,
            original_error=error,
            severity=ErrorSeverity.RETRYABLE_TRANSIENT,
            retry_after=2.0,
        )

    # 인증 관련 키워드
    if any(
        kw in error_str
        for kw in ["auth", "permission", "forbidden", "401", "403", "api key"]
    ):
        return NexloopError(
            code=ErrorCode.AUTH_FAILED,
            original_error=error,
            severity=ErrorSeverity.PERMANENT,
        )

    # Rate Limit 관련
    if any(kw in error_str for kw in ["rate limit", "quota", "429", "too many"]):
        return NexloopError(
            code=ErrorCode.API_RATE_LIMIT,
            original_error=error,
            severity=ErrorSeverity.RETRYABLE_TRANSIENT,
            retry_after=5.0,
        )

    # 데이터 관련
    if any(kw in error_str for kw in ["not found", "없습니다", "404"]):
        return NexloopError(
            code=ErrorCode.DATA_NOT_FOUND,
            original_error=error,
            severity=ErrorSeverity.PERMANENT,
        )

    # JSON 파싱 관련
    if any(kw in error_str for kw in ["json", "parse", "decode"]):
        return NexloopError(
            code=ErrorCode.DATA_PARSE_ERROR,
            original_error=error,
            severity=ErrorSeverity.RETRYABLE_PERMANENT,
        )

    # 기본: 알 수 없는 에러
    return NexloopError(
        code=ErrorCode.UNKNOWN_ERROR,
        original_error=error,
        severity=ErrorSeverity.RETRYABLE_TRANSIENT,
    )


def handle_error(error: Exception, context: str = "") -> str:
    """
    에러를 처리하고 사용자 친화적인 메시지를 반환합니다.

    Args:
        error: 발생한 예외
        context: 에러 발생 컨텍스트 (예: "YouTube 검색", "PDF 생성")

    Returns:
        사용자에게 표시할 에러 메시지
    """
    nexloop_error = error if isinstance(error, NexloopError) else classify_error(error)

    # 컨텍스트가 있으면 메시지에 추가
    if context:
        return f"{context} 중 오류 발생: {nexloop_error.user_message}"

    return nexloop_error.user_message
