"""
PII (개인식별정보) 자동 탐지 및 마스킹 유틸리티

Nexloop Guard의 Auto-Compliance 파이프라인에서 사용:
- 전화번호, 이메일, 주민등록번호, 카드번호, 계좌번호 등 탐지
- 탐지된 PII를 마스킹 처리하여 개인정보 보호
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class PIIType(str, Enum):
    """PII 유형 분류"""

    PHONE = "phone"
    EMAIL = "email"
    RESIDENT_ID = "resident_id"
    CARD_NUMBER = "card_number"
    ACCOUNT_NUMBER = "account_number"
    IP_ADDRESS = "ip_address"
    LICENSE_PLATE = "license_plate"


@dataclass
class PIIMatch:
    """탐지된 PII 항목"""

    pii_type: PIIType
    original: str
    masked: str
    start: int
    end: int


@dataclass
class PIIMaskResult:
    """PII 마스킹 결과"""

    original_text: str
    masked_text: str
    pii_found: list[PIIMatch] = field(default_factory=list)
    pii_count: int = 0

    @property
    def has_pii(self) -> bool:
        """PII가 발견되었는지 여부"""
        return self.pii_count > 0


# PII 패턴 정의 (한국 기준 + 범용)
_PII_PATTERNS: list[tuple[PIIType, re.Pattern, str]] = [
    # 한국 전화번호 (010-1234-5678, 02-123-4567 등)
    (
        PIIType.PHONE,
        re.compile(
            r"(?<!\d)"
            r"(0[12]\d?[-.\s]?\d{3,4}[-.\s]?\d{4})"
            r"(?!\d)"
        ),
        "***-****-****",
    ),
    # 이메일 주소
    (
        PIIType.EMAIL,
        re.compile(
            r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
        ),
        "***@***.***",
    ),
    # 주민등록번호 (123456-1234567)
    (
        PIIType.RESIDENT_ID,
        re.compile(
            r"(?<!\d)"
            r"(\d{6})[-\s]?([1-4]\d{6})"
            r"(?!\d)"
        ),
        "******-*******",
    ),
    # 신용카드 번호 (4자리-4자리-4자리-4자리)
    (
        PIIType.CARD_NUMBER,
        re.compile(
            r"(?<!\d)"
            r"(\d{4})[-\s]?(\d{4})[-\s]?(\d{4})[-\s]?(\d{4})"
            r"(?!\d)"
        ),
        "****-****-****-****",
    ),
    # 계좌번호 (10-14자리 연속 숫자, 하이픈 허용)
    (
        PIIType.ACCOUNT_NUMBER,
        re.compile(
            r"(?<!\d)"
            r"(\d{3,6})[-\s](\d{2,6})[-\s](\d{2,6})"
            r"(?!\d)"
        ),
        "***-**-******",
    ),
    # IP 주소
    (
        PIIType.IP_ADDRESS,
        re.compile(
            r"(?<!\d)"
            r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
            r"(?!\d)"
        ),
        "***.***.***.***",
    ),
    # 한국 차량 번호판 (12가1234, 서울12가1234 등)
    (
        PIIType.LICENSE_PLATE,
        re.compile(
            r"(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)?"
            r"\s?\d{2,3}\s?[가-힣]\s?\d{4}"
        ),
        "**가****",
    ),
]


def detect_pii(text: str) -> list[PIIMatch]:
    """
    텍스트에서 PII를 탐지한다.

    Args:
        text: 검사할 텍스트

    Returns:
        탐지된 PII 항목 리스트
    """
    if not text:
        return []

    matches: list[PIIMatch] = []
    seen_spans: set[tuple[int, int]] = set()

    for pii_type, pattern, mask_template in _PII_PATTERNS:
        for match in pattern.finditer(text):
            span = (match.start(), match.end())
            # 겹치는 매치 방지
            if any(
                s <= span[0] < e or s < span[1] <= e
                for s, e in seen_spans
            ):
                continue

            seen_spans.add(span)
            matches.append(
                PIIMatch(
                    pii_type=pii_type,
                    original=match.group(),
                    masked=mask_template,
                    start=match.start(),
                    end=match.end(),
                )
            )

    # 위치 순으로 정렬
    matches.sort(key=lambda m: m.start)
    return matches


def mask_pii(text: str) -> PIIMaskResult:
    """
    텍스트에서 PII를 탐지하고 마스킹 처리한다.

    Args:
        text: 마스킹할 텍스트

    Returns:
        PIIMaskResult (원문, 마스킹 결과, 탐지 내역)
    """
    if not text:
        return PIIMaskResult(
            original_text=text,
            masked_text=text,
            pii_found=[],
            pii_count=0,
        )

    pii_matches = detect_pii(text)

    if not pii_matches:
        return PIIMaskResult(
            original_text=text,
            masked_text=text,
            pii_found=[],
            pii_count=0,
        )

    # 뒤에서부터 치환하여 인덱스 유지
    masked = text
    for m in reversed(pii_matches):
        masked = masked[: m.start] + m.masked + masked[m.end :]

    return PIIMaskResult(
        original_text=text,
        masked_text=masked,
        pii_found=pii_matches,
        pii_count=len(pii_matches),
    )


def contains_pii(text: str) -> bool:
    """텍스트에 PII가 포함되어 있는지 빠르게 확인"""
    return len(detect_pii(text)) > 0
