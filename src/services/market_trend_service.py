"""
시장 트렌드 분석 서비스
Discovery Engine 검색 결과를 요약
"""

import asyncio
from typing import Any

from core.interfaces.chatbot import IRAGClient
from utils.logger import log_info, log_warning


class MarketTrendService:
    """시장 트렌드 분석 서비스"""

    def __init__(self, rag_client: IRAGClient) -> None:
        self._rag_client = rag_client

    def get_market_trends(self, product: dict, max_results: int = 5) -> dict[str, Any]:
        """시장 동향을 조회합니다 (동기 래퍼).

        내부 RAG 클라이언트(DiscoveryEngineClient.search)가 async 이므로,
        이벤트 루프가 없는 환경에서는 asyncio.run()으로 실행합니다.

        주의: 이미 실행 중인 이벤트 루프(예: FastAPI async)에서는
        이 메서드를 호출하지 말고 `get_market_trends_async()`를 await 하세요.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.get_market_trends_async(product, max_results=max_results))

        raise RuntimeError(
            "동작 중인 이벤트 루프에서 get_market_trends()를 호출할 수 없습니다. "
            "get_market_trends_async()를 사용하세요."
        )

    async def get_market_trends_async(
        self, product: dict, max_results: int = 5
    ) -> dict[str, Any]:
        product_name = product.get("name", "")
        product_category = product.get("category", "")
        query = " ".join([item for item in [product_category, product_name, "시장 동향"] if item])

        if not query.strip():
            log_warning("시장 동향 검색을 위한 쿼리가 비어 있습니다.")
            return {"query": "", "issues": [], "raw_results": []}

        # IRAGClient.search 는 async 인터페이스(DiscoveryEngineClient.search)로 사용한다.
        results = await self._rag_client.search(query, max_results=max_results)

        issues = []
        for item in results[:3]:
            issues.append({
                "title": item.get("title", ""),
                "summary": item.get("snippet", ""),
                "url": item.get("url", ""),
            })

        log_info(f"시장 동향 검색 완료: '{query}' -> {len(issues)}개 이슈")
        return {"query": query, "issues": issues, "raw_results": results}
