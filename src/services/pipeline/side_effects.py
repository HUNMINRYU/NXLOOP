"""Side Effects System - 비동기 부수효과 (fire-and-forget)"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)


class SideEffectManager:
    """
    파이프라인 이벤트 발생 시 비동기 side effect 실행.
    분석 로깅, 캐시 워밍, 프로필 업데이트 등을 non-blocking으로 처리.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[..., Coroutine[Any, Any, None]]]] = {}
        self._pending_tasks: list[asyncio.Task[None]] = []

    def on(
        self, event: str, handler: Callable[..., Coroutine[Any, Any, None]]
    ) -> None:
        """이벤트 핸들러 등록"""
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def emit(self, event: str, **kwargs: Any) -> None:
        """이벤트 발생 (fire-and-forget)"""
        handlers = self._handlers.get(event, [])
        for handler in handlers:
            try:
                task = asyncio.create_task(self._safe_run(handler, event, **kwargs))
                self._pending_tasks.append(task)
            except RuntimeError:
                # 이벤트 루프가 없는 경우 무시
                logger.debug(f"Side effect '{event}' 스킵 (이벤트 루프 없음)")

    async def _safe_run(
        self,
        handler: Callable[..., Coroutine[Any, Any, None]],
        event: str,
        **kwargs: Any,
    ) -> None:
        """안전하게 핸들러 실행 (예외 무시)"""
        try:
            await handler(**kwargs)
        except Exception as e:
            logger.warning(f"Side effect '{event}' 실패: {e}")

    async def flush(self) -> None:
        """모든 pending side effect 완료 대기"""
        if self._pending_tasks:
            await asyncio.gather(*self._pending_tasks, return_exceptions=True)
            self._pending_tasks.clear()
