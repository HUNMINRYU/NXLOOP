from __future__ import annotations

from typing import Any

from services.naver_service import NaverService
from services.rag_ingestion_service import RagIngestionService
from services.youtube_service import YouTubeService
from utils.logger import get_logger

logger = get_logger(__name__)


class InsightExternalService:
    """Collect external insight sources and ingest them into Discovery Engine."""

    def __init__(
        self,
        naver_service: NaverService,
        youtube_service: YouTubeService,
        rag_ingestion_service: RagIngestionService,
    ) -> None:
        self._naver = naver_service
        self._youtube = youtube_service
        self._rag_ingestion = rag_ingestion_service

    def ingest_naver(
        self,
        query: str,
        max_results: int = 10,
        include_products: bool = True,
        include_blogs: bool = True,
        include_news: bool = True,
        meta: dict[str, str | None] | None = None,
        user: Any | None = None,
    ) -> dict[str, int]:
        safe_query = (query or "").strip()
        if not safe_query:
            return {"ingested": 0, "items": 0, "products": 0, "blogs": 0, "news": 0}

        meta = meta or {}
        items: list[dict[str, Any]] = []
        products: list[dict[str, Any]] = []
        blogs: list[dict[str, Any]] = []
        news: list[dict[str, Any]] = []

        if include_products:
            try:
                products = self._naver.search_products(safe_query, max_results)
            except Exception as exc:
                logger.warning(f"Naver shopping search failed: {exc}")

        if include_blogs:
            try:
                blogs = self._naver.search_blog(safe_query, max_results)
            except Exception as exc:
                logger.warning(f"Naver blog search failed: {exc}")

        if include_news:
            try:
                news = self._naver.search_news(safe_query, max_results)
            except Exception as exc:
                logger.warning(f"Naver news search failed: {exc}")

        for item in products:
            title = item.get("title") or safe_query
            content = "\n".join(
                [
                    f"Product: {title}",
                    f"Price: {item.get('price', '')}",
                    f"Brand: {item.get('brand', '')}",
                    f"Mall: {item.get('mall', '')}",
                    f"Categories: {item.get('category1', '')} {item.get('category2', '')}",
                    f"Link: {item.get('link', '')}",
                ]
            ).strip()
            items.append(
                {
                    "title": title,
                    "content": content,
                    "doc_type": "trend_search",
                    "source": "naver_shopping",
                    "campaign_name": meta.get("campaign_name"),
                    "channel": meta.get("channel"),
                    "region": meta.get("region"),
                    "period_start": meta.get("period_start"),
                    "period_end": meta.get("period_end"),
                    "tags": [safe_query, "naver", "shopping"],
                }
            )

        for item in blogs:
            title = item.get("title") or safe_query
            content = "\n".join(
                [
                    f"Title: {title}",
                    item.get("description", ""),
                    f"Blogger: {item.get('blogger', '')}",
                    f"Date: {item.get('post_date', '')}",
                    f"Link: {item.get('link', '')}",
                ]
            ).strip()
            items.append(
                {
                    "title": title,
                    "content": content,
                    "doc_type": "social_trend",
                    "source": "naver_blog",
                    "campaign_name": meta.get("campaign_name"),
                    "channel": meta.get("channel"),
                    "region": meta.get("region"),
                    "period_start": meta.get("period_start"),
                    "period_end": meta.get("period_end"),
                    "tags": [safe_query, "naver", "blog"],
                }
            )

        for item in news:
            title = item.get("title") or safe_query
            content = "\n".join(
                [
                    f"Title: {title}",
                    item.get("description", ""),
                    f"Published: {item.get('published_at', '')}",
                    f"Link: {item.get('link', '')}",
                    f"Origin: {item.get('origin', '')}",
                ]
            ).strip()
            items.append(
                {
                    "title": title,
                    "content": content,
                    "doc_type": "news_summary",
                    "source": "naver_news",
                    "campaign_name": meta.get("campaign_name"),
                    "channel": meta.get("channel"),
                    "region": meta.get("region"),
                    "period_start": meta.get("period_start"),
                    "period_end": meta.get("period_end"),
                    "tags": [safe_query, "naver", "news"],
                }
            )

        ingested = self._rag_ingestion.ingest_manual_upload(items, user)
        return {
            "ingested": int(ingested),
            "items": len(items),
            "products": len(products),
            "blogs": len(blogs),
            "news": len(news),
        }

    def ingest_youtube(
        self,
        query: str,
        max_results: int = 5,
        include_comments: bool = True,
        meta: dict[str, str | None] | None = None,
        user: Any | None = None,
    ) -> dict[str, int]:
        safe_query = (query or "").strip()
        if not safe_query:
            return {"ingested": 0, "items": 0, "videos": 0}

        meta = meta or {}
        # collect_product_data expects a product dict with 'name'
        try:
            yt_data = self._youtube.collect_product_data(
                {"name": safe_query},
                max_results=max_results,
                include_comments=include_comments
            )
        except Exception as exc:
            logger.error(f"YouTube data collection failed: {exc}")
            return {"ingested": 0, "items": 0, "videos": 0}

        videos = yt_data.get("videos", [])
        items: list[dict[str, Any]] = []

        for video in videos:
            title = video.get("title") or safe_query
            # Basic video content
            content_parts = [
                f"Video Title: {title}",
                f"Uploader: {video.get('uploader', 'N/A')}",
                f"Description: {video.get('description', '')}",
                f"Viedeo ID: {video.get('video_id', '')}",
                f"Link: https://www.youtube.com/watch?v={video.get('video_id', '')}"
            ]

            # Add comments to content if available
            comments = video.get("comments", [])
            if comments:
                content_parts.append("Key Comments:")
                for c in comments[:10]: # Up to 10 comments
                    content_parts.append(f"- {c.get('text', '')}")

            content = "\n".join(content_parts).strip()

            items.append(
                {
                    "title": title,
                    "content": content,
                    "doc_type": "social_trend",
                    "source": "youtube",
                    "campaign_name": meta.get("campaign_name"),
                    "channel": meta.get("channel"),
                    "region": meta.get("region"),
                    "period_start": meta.get("period_start"),
                    "period_end": meta.get("period_end"),
                    "tags": [safe_query, "youtube", "video"],
                }
            )

        ingested = self._rag_ingestion.ingest_manual_upload(items, user)
        return {
            "ingested": int(ingested),
            "items": len(items),
            "videos": len(videos),
        }
