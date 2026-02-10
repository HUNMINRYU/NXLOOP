"""
데이터 품질 검증 로직
"""

import re

from pydantic import BaseModel, Field, field_validator


class ValidatedComment(BaseModel):
    """검증된 댓글 데이터 모델"""

    author: str = Field(..., min_length=1)
    text: str = Field(..., min_length=5)
    likes: int = Field(0, ge=0)

    @field_validator("text")
    @classmethod
    def clean_text(cls, value: str) -> str:
        spam_patterns = [r"http[s]?://", r"카톡|텔레그램|연락주세요"]
        for pattern in spam_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError("스팸 댓글 필터링됨")
        return value.strip()


class DataQualityReport(BaseModel):
    """데이터 품질 보고서"""

    total_count: int
    valid_count: int
    rejected_count: int
    quality_score: float
    avg_length: float = Field(default=0.0, description="유효 댓글 평균 길이")
    spam_rate: float = Field(default=0.0, description="스팸 비율 (0.0~1.0)")
    duplicate_rate: float = Field(default=0.0, description="중복 비율 (0.0~1.0)")


def validate_comments(
    raw_comments: list[dict],
) -> tuple[list[ValidatedComment], DataQualityReport]:
    valid: list[ValidatedComment] = []
    rejected = 0
    for comment in raw_comments:
        try:
            valid.append(ValidatedComment(**comment))
        except Exception:
            rejected += 1

    total = len(raw_comments)

    # 확장 품질 메트릭 계산
    avg_length = 0.0
    if valid:
        avg_length = sum(len(c.text) for c in valid) / len(valid)

    spam_rate = rejected / max(total, 1)

    # 중복 비율 계산
    texts = [c.text for c in valid]
    unique_count = len(set(texts))
    duplicate_rate = 1 - (unique_count / max(len(texts), 1)) if texts else 0.0

    report = DataQualityReport(
        total_count=total,
        valid_count=len(valid),
        rejected_count=rejected,
        quality_score=len(valid) / max(total, 1),
        avg_length=round(avg_length, 1),
        spam_rate=round(spam_rate, 4),
        duplicate_rate=round(duplicate_rate, 4),
    )
    return valid, report
