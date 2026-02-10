import asyncio
import uuid
from datetime import datetime
from typing import Any

import numpy as np

from infrastructure.clients.gemini_client import GeminiClient
from services.pipeline.types import AuthorInfo, Candidate
from utils.logger import get_logger, log_feature_end, log_feature_start

logger = get_logger(__name__)


MAX_CONCURRENT_EMBEDDINGS = 5


class TwoTowerSource:
    """
    X-Algorithm 'Phoenix' Two-Tower 모델 고도화:
    - Embedding Caching: 동일한 텍스트에 대한 임베딩 호출 최소화
    - Batch Processing: (추후 확장용) 다량의 소스 동시 처리
    """

    def __init__(self, gemini_client: GeminiClient | None = None):
        self.gemini_client = gemini_client or GeminiClient()
        self._vector_cache: dict[str, np.ndarray] = {}  # 메모리 내 벡터 캐시
        self._embedding_semaphore = asyncio.Semaphore(MAX_CONCURRENT_EMBEDDINGS)

    async def item_to_candidate(
        self,
        raw_items: list[dict[str, Any]],
        brand_context: str = ""
    ) -> list[Candidate]:
        """
        브랜드와 콘텐츠의 정렬(Alignment)을 기반으로 소싱 점수 산정
        """
        if not raw_items:
            return []

        log_feature_start("xalgo_two_tower", f"raw_items={len(raw_items)}")

        def _tokenize(text: str) -> list[str]:
            # 간단한 토큰화(공백 기반). 한국어의 경우 완벽하진 않지만 BM25 신호로는 충분히 유용함.
            return [t for t in (text or "").lower().split() if t]

        # 1. Brand Tower 생성 (캐싱 적용)
        brand_text = brand_context or "General interesting marketing content"
        cache_hit_brand = 1 if brand_text in self._vector_cache else 0
        brand_vector = await self._get_embedding_cached(brand_text)

        # 2. 모든 아이템에 대해 병렬로 콘텐츠 벡터 생성
        contents_for_bm25: list[str] = []
        tasks = []
        for item in raw_items:
            content_to_embed = f"{item.get('title', '')} {item.get('text', '')}"[:1000]
            contents_for_bm25.append(content_to_embed)
            # 캐시 히트는 빠른 운영 판단을 위한 참고값 (정확한 hit/miss 보장은 아님)
            tasks.append(self._get_embedding_cached(content_to_embed))

        content_vectors = await asyncio.gather(*tasks)
        cache_hit_contents = sum(1 for t in contents_for_bm25 if t in self._vector_cache)

        # 2.5 BM25 점수 계산(가능한 경우). 실패하면 0으로 fallback.
        bm25_norm_scores: list[float] = [0.0 for _ in raw_items]
        bm25_ok = False
        try:
            from rank_bm25 import BM25Okapi

            corpus = [_tokenize(doc) for doc in contents_for_bm25]
            bm25 = BM25Okapi(corpus)
            raw_scores = list(bm25.get_scores(_tokenize(brand_text)))
            if raw_scores:
                s_min = min(raw_scores)
                s_max = max(raw_scores)
                if s_max > s_min:
                    bm25_norm_scores = [(s - s_min) / (s_max - s_min) for s in raw_scores]
                else:
                    bm25_norm_scores = [0.0 for _ in raw_scores]
            bm25_ok = True
        except Exception as e:
            logger.warning(f"BM25 계산 실패(무시하고 진행): {e}")

        candidates = []
        for item, content_vector, bm25_norm in zip(
            raw_items, content_vectors, bm25_norm_scores, strict=True
        ):
            # 3. Similarity Score 계산
            dense_sim = float(self._cosine_similarity(brand_vector, content_vector))
            # cosine similarity(-1..1)를 0..1로 정규화 후 하이브리드 결합
            dense_norm = max(0.0, min(1.0, (dense_sim + 1.0) / 2.0))
            hybrid_score = 0.7 * dense_norm + 0.3 * float(bm25_norm or 0.0)

            c_id = str(item.get("id", uuid.uuid4()))
            candidate = Candidate(
                id=c_id,
                content=item.get("text", ""),
                title=item.get("title", ""),
                author=AuthorInfo(username=item.get("author", "Anonymous")),
                created_at=datetime.now(),
                like_count=int(item.get("likes", 0)) if str(item.get("likes", "0")).isdigit() else 0,
                category=item.get("category", "general"),
            )

            # 벡터 데이터 보존 (Semantic Diversity 단계에서 재사용)
            candidate.metadata["embedding"] = content_vector.tolist()
            candidate.metadata["two_tower_dense_sim"] = round(dense_sim, 4)
            candidate.metadata["bm25_norm"] = round(float(bm25_norm or 0.0), 4)
            candidate.metadata["two_tower_hybrid"] = round(float(hybrid_score), 4)
            candidate.score.raw_score = float(hybrid_score) * 10.0

            candidates.append(candidate)

        log_feature_end(
            "xalgo_two_tower",
            extra_detail=(
                f"candidates={len(candidates)} "
                f"embed_cache_hit~={cache_hit_contents + cache_hit_brand}/{len(contents_for_bm25) + 1} "
                f"bm25={'ok' if bm25_ok else 'fail'}"
            ),
        )
        return candidates

    async def _get_embedding_cached(self, text: str) -> np.ndarray:
        """캐시를 사용하여 임베딩 가져오기 (비용 및 속도 최적화)"""
        cache_key = text.strip()
        if cache_key in self._vector_cache:
            return self._vector_cache[cache_key]

        async with self._embedding_semaphore:
            # 세마포어 대기 중 다른 태스크가 캐시에 저장했을 수 있음
            if cache_key in self._vector_cache:
                return self._vector_cache[cache_key]

            try:
                vector = await self.gemini_client.get_embedding(text)
                vec_np = np.array(vector)
                # 최대 1000개까지 결과 캐싱 (간이 메모리 관리)
                if len(self._vector_cache) < 1000:
                    self._vector_cache[cache_key] = vec_np
                return vec_np
            except Exception as e:
                logger.error(f"임베딩 생성 실패: {e}")
                return np.zeros(768)

    def _cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        if np.all(v1 == 0) or np.all(v2 == 0):
            return 0.0
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        return np.dot(v1, v2) / (norm1 * norm2)

# 하위 호환성을 위한 별칭 설정
CommentSource = TwoTowerSource
