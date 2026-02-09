from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol, cast

from utils.logger import get_logger

logger = get_logger(__name__)


UTC = timezone.utc


class YouTubeLikeClient(Protocol):
    def search(self, query: str, max_results: int = 3) -> list[dict[str, Any]]: ...

    def get_video_details(self, video_id: str) -> dict[str, Any] | None: ...


@dataclass(frozen=True)
class DiskCacheConfig:
    cache_dir: Path
    ttl_sec: int = 24 * 3600
    cache_only: bool = False


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_fresh(*, cached_at_iso: str | None, ttl_sec: int, now: datetime) -> bool:
    if ttl_sec <= 0:
        return False
    cached_at = _parse_iso(cached_at_iso)
    if cached_at is None:
        return False
    return (now - cached_at) <= timedelta(seconds=int(ttl_sec))


class DiskCachedYouTubeClient:
    """
    YouTubeClient를 감싸는 "디스크 캐시" 래퍼.

    - 목적: 네트워크/쿼터 변동과 무관하게 동일한 입력으로 동일한 데이터셋/리포트를 재현.
    - 주의: cache_only 모드에서는 캐시 파일이 없으면 실패한다.
    """

    def __init__(self, *, inner: YouTubeLikeClient, config: DiskCacheConfig) -> None:
        self._inner = inner
        self._config = config

        (self._config.cache_dir / "search").mkdir(parents=True, exist_ok=True)
        (self._config.cache_dir / "details").mkdir(parents=True, exist_ok=True)

    def _read_cache(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            raise ValueError(f"캐시 JSON 파싱 실패: {path}") from e
        if not isinstance(data, dict):
            return None
        return data

    def _write_cache(self, path: Path, value: Any, *, now: datetime) -> None:
        payload = {"cached_at_iso": now.astimezone(UTC).isoformat(), "value": value}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def search(self, query: str, max_results: int = 3) -> list[dict[str, Any]]:
        now = datetime.now(tz=UTC)
        key = _sha256_hex(f"search|q={query}|max={int(max_results)}")
        path = self._config.cache_dir / "search" / f"{key}.json"

        cached = self._read_cache(path)
        if cached is not None and _is_fresh(
            cached_at_iso=str(cached.get("cached_at_iso") or ""),
            ttl_sec=int(self._config.ttl_sec),
            now=now,
        ):
            value = cached.get("value")
            if isinstance(value, list) and all(isinstance(x, dict) for x in value):
                return cast(list[dict[str, Any]], value)

        if self._config.cache_only:
            raise FileNotFoundError(f"cache_only 모드에서 search 캐시를 찾지 못했습니다: {path}")

        try:
            value = self._inner.search(query, max_results=int(max_results))
        except Exception as e:
            # 네트워크 실패 시에도, 캐시가 있으면 fallback 하는 편이 실험 재현에 유리하다.
            if cached is not None and isinstance(cached.get("value"), list):
                logger.warning("YouTube search 실패, 캐시로 대체합니다.")
                fallback = cached.get("value")
                if isinstance(fallback, list) and all(isinstance(x, dict) for x in fallback):
                    return cast(list[dict[str, Any]], fallback)
            raise RuntimeError("YouTube search 실패") from e

        self._write_cache(path, value, now=now)
        return value

    def get_video_details(self, video_id: str) -> dict[str, Any] | None:
        now = datetime.now(tz=UTC)
        safe_id = str(video_id).strip()
        key = _sha256_hex(f"details|id={safe_id}")
        path = self._config.cache_dir / "details" / f"{key}.json"

        cached = self._read_cache(path)
        if cached is not None and _is_fresh(
            cached_at_iso=str(cached.get("cached_at_iso") or ""),
            ttl_sec=int(self._config.ttl_sec),
            now=now,
        ):
            value = cached.get("value")
            if isinstance(value, dict):
                return cast(dict[str, Any], value)
            if value is None:
                return None

        if self._config.cache_only:
            raise FileNotFoundError(
                f"cache_only 모드에서 details 캐시를 찾지 못했습니다: {path}"
            )

        try:
            value = self._inner.get_video_details(safe_id)
        except Exception as e:
            if cached is not None and (
                isinstance(cached.get("value"), dict) or cached.get("value") is None
            ):
                logger.warning("YouTube get_video_details 실패, 캐시로 대체합니다.")
                fallback = cached.get("value")
                if isinstance(fallback, dict):
                    return cast(dict[str, Any], fallback)
                return None
            raise RuntimeError("YouTube get_video_details 실패") from e

        self._write_cache(path, value, now=now)
        return value
