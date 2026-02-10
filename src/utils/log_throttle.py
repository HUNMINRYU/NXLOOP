"""
고빈도 endpoint 로깅 스팸을 줄이기 위한 간단한 in-memory throttle 유틸리티.

- 전역 로깅 전략(log_feature_*) 자체를 바꾸지 않고,
  특정 엔드포인트에서만 `should_log_throttled()` 결과로 start/end 로깅을 제어한다.
- 실패/에러 로그는 호출부에서 별도로 항상 출력하도록 한다(이 모듈은 관여하지 않음).
"""

from __future__ import annotations

import threading
import time
from typing import Final

_LOCK: Final[threading.Lock] = threading.Lock()
_LAST_LOG_TS: dict[str, float] = {}

# 메모리 누수 방지용의 보수적인 상한/정리 기준 (고빈도 폴링에서도 안전하게 동작)
_MAX_KEYS: Final[int] = 10_000
_PRUNE_OLDER_THAN_SEC: Final[float] = 300.0  # 5분 이상 지난 키는 정리 대상


def should_log_throttled(
    key: str, interval_sec: float, now: float | None = None
) -> bool:
    """주어진 key에 대해 interval_sec 간격으로 1회만 True를 반환한다.

    Args:
        key: throttle 식별자(예: "{feature}:{task_id}")
        interval_sec: 허용 간격(초). 0 이하이면 항상 True.
        now: 테스트를 위한 현재 시간(초, monotonic 기준). None이면 time.monotonic() 사용.

    Returns:
        True: 이번 호출에서 로그를 찍어도 됨(호출부에서 start/end 출력)
        False: 스팸 방지를 위해 이번 호출은 로그 생략
    """
    if interval_sec <= 0:
        return True

    ts = time.monotonic() if now is None else float(now)
    with _LOCK:
        last = _LAST_LOG_TS.get(key)
        if last is not None and ts - last < interval_sec:
            return False

        _LAST_LOG_TS[key] = ts
        if len(_LAST_LOG_TS) > _MAX_KEYS:
            _prune(now_ts=ts)
        return True


def _prune(now_ts: float) -> None:
    cutoff = now_ts - _PRUNE_OLDER_THAN_SEC
    for k, v in list(_LAST_LOG_TS.items()):
        if v < cutoff:
            _LAST_LOG_TS.pop(k, None)


def _reset_for_tests() -> None:
    """테스트에서만 사용: throttle 상태 초기화."""
    with _LOCK:
        _LAST_LOG_TS.clear()
