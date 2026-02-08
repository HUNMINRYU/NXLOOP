from collections.abc import Iterable
from typing import ClassVar

from config.settings import get_settings
from services.pipeline.types import Candidate
from utils.pii_masker import contains_pii, mask_pii


class QualityFilter:
    """
    X-Algorithm의 Pre-Scoring Filtering 단계
    스팸, 중복, 저품질, PII 포함 콘텐츠를 사전에 제거하여
    Scoring 연산 낭비 방지 및 개인정보 보호
    """

    MIN_LENGTH: ClassVar[int] = 5
    SPAM_KEYWORDS: ClassVar[list[str]] = ["광고", "홍보", "http", "카톡", "사다리", "토토"]

    def __init__(
        self,
        custom_banned_keywords: Iterable[str] | None = None,
        *,
        mask_pii_content: bool = True,
    ) -> None:
        if custom_banned_keywords is None:
            custom_banned_keywords = get_settings().brand_banned_keywords
        self._custom_banned_keywords = [
            keyword.strip() for keyword in custom_banned_keywords if keyword.strip()
        ]
        self._mask_pii = mask_pii_content

    def filter(self, candidates: list[Candidate]) -> list[Candidate]:
        filtered_candidates = []
        for candidate in candidates:
            if self._is_eligible(candidate):
                # PII 마스킹 (콘텐츠 유지, 개인정보만 마스킹)
                if self._mask_pii:
                    candidate = self._apply_pii_masking(candidate)
                filtered_candidates.append(candidate)
        return filtered_candidates

    def _apply_pii_masking(self, candidate: Candidate) -> Candidate:
        """콘텐츠 내 PII를 마스킹 처리"""
        if not contains_pii(candidate.content):
            return candidate

        result = mask_pii(candidate.content)
        candidate.content = result.masked_text
        candidate.metadata["pii_masked"] = True
        candidate.metadata["pii_count"] = result.pii_count
        candidate.metadata["pii_types"] = [
            m.pii_type.value for m in result.pii_found
        ]
        return candidate

    def _is_eligible(self, candidate: Candidate) -> bool:
        # 1. 길이 필터
        if len(candidate.content.strip()) < self.MIN_LENGTH:
            return False

        # 2. 스팸 키워드 필터
        for keyword in self.SPAM_KEYWORDS:
            if keyword in candidate.content:
                return False

        # 2-1. 커스텀 금지어 필터
        for keyword in self._custom_banned_keywords:
            if keyword in candidate.content:
                return False

        # 3. Toxicity 필터 (이미 Feature가 있다면)
        return not candidate.features.toxicity > 0.8
