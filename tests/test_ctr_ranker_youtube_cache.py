from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.ctr_ranker_youtube_cache import DiskCacheConfig, DiskCachedYouTubeClient

UTC = timezone.utc


class FakeYouTubeClient:
    def __init__(self) -> None:
        self.search_calls: int = 0
        self.details_calls: int = 0

    def search(self, query: str, max_results: int = 3) -> list[dict]:
        self.search_calls += 1
        return [{"id": "v1", "title": query, "max_results": max_results}]

    def get_video_details(self, video_id: str) -> dict | None:
        self.details_calls += 1
        return {"id": video_id, "view_count": 123}


def test_cache_only_missing_raises(tmp_path: Path) -> None:
    inner = FakeYouTubeClient()
    cfg = DiskCacheConfig(cache_dir=tmp_path, ttl_sec=3600, cache_only=True)
    cached = DiskCachedYouTubeClient(inner=inner, config=cfg)

    with pytest.raises(FileNotFoundError):
        cached.search("q", max_results=1)

    with pytest.raises(FileNotFoundError):
        cached.get_video_details("vid")


def test_cache_hit_returns_without_calling_inner(tmp_path: Path) -> None:
    inner = FakeYouTubeClient()
    cfg = DiskCacheConfig(cache_dir=tmp_path, ttl_sec=3600, cache_only=False)
    cached = DiskCachedYouTubeClient(inner=inner, config=cfg)

    # warm
    out1 = cached.search("hello", max_results=2)
    assert inner.search_calls == 1
    # hit
    out2 = cached.search("hello", max_results=2)
    assert inner.search_calls == 1
    assert out1 == out2


def test_expired_cache_calls_inner_and_rewrites(tmp_path: Path) -> None:
    inner = FakeYouTubeClient()
    cfg = DiskCacheConfig(cache_dir=tmp_path, ttl_sec=1, cache_only=False)
    cached = DiskCachedYouTubeClient(inner=inner, config=cfg)

    out1 = cached.get_video_details("vid")
    assert inner.details_calls == 1
    assert out1 == {"id": "vid", "view_count": 123}

    # force-expire all cached files by editing cached_at_iso
    details_dir = tmp_path / "details"
    files = list(details_dir.glob("*.json"))
    assert files
    for f in files:
        obj = json.loads(f.read_text(encoding="utf-8"))
        obj["cached_at_iso"] = (datetime.now(tz=UTC) - timedelta(hours=3)).isoformat()
        f.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

    out2 = cached.get_video_details("vid")
    assert inner.details_calls == 2
    assert out2 == {"id": "vid", "view_count": 123}
