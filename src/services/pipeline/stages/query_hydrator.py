"""Query Hydration - 파이프라인 실행 전 제품/브랜드 컨텍스트 보강"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QueryContext:
    """파이프라인 실행 컨텍스트"""

    product_id: str = ""
    brand_keywords: list[str] = field(default_factory=list)
    historical_performance: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class QueryHydrator:
    """
    파이프라인 실행 전 제품/브랜드 컨텍스트를 풍부하게 로드.
    제품 메타데이터, 과거 성과 데이터 등을 QueryContext에 집약.
    """

    def __init__(
        self,
        product_metadata: dict[str, Any] | None = None,
        performance_data: dict[str, Any] | None = None,
    ):
        self._product_metadata = product_metadata or {}
        self._performance_data = performance_data or {}

    def hydrate(self, product_id: str) -> QueryContext:
        """제품 ID로 컨텍스트 로드"""
        meta = self._product_metadata.get(product_id, {})
        perf = self._performance_data.get(product_id, {})

        return QueryContext(
            product_id=product_id,
            brand_keywords=meta.get("brand_keywords", []),
            historical_performance=perf,
            metadata=meta,
        )
