from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AuthorInfo:
    """댓글 작성자 정보"""

    username: str
    is_verified: bool = False
    reputation_score: float = 0.0


@dataclass
class CandidateFeatures:
    """LLM 및 분석을 통해 추출된 Feature (0.0 ~ 1.0)"""

    # 긍정적 액션
    purchase_intent: float = 0.0
    constructive_feedback: float = 0.0
    reply_inducing: float = 0.0
    share_probability: float = 0.0
    viral_potential: float = 0.0
    actionable_insight: float = 0.0
    quote_worthy: float = 0.0
    save_worthy: float = 0.0
    follow_author: float = 0.0

    # 중립 액션
    sentiment_intensity: float = 0.0
    dwell_time: float = 0.0

    # 부정적 액션
    toxicity: float = 0.0
    controversy_score: float = 0.0
    not_interested: float = 0.0
    report_probability: float = 0.0

    # 확장 시그널 (x-algorithm 19개 engagement prediction)
    dm_probability: float = 0.0       # DM/문의 유도 가능성
    copy_link_probability: float = 0.0  # 링크 공유 가능성
    profile_click: float = 0.0        # 프로필 클릭 가능성
    bookmark_worthy: float = 0.0      # 북마크 저장 가능성

    # 추가 메타데이터
    keywords: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)


@dataclass
class CandidateScore:
    """스코어링 단계의 결과"""

    final_score: float = 0.0
    raw_score: float = 0.0           # 보정 전 점수
    positive_score: float = 0.0      # 긍정 시그널 합
    negative_score: float = 0.0      # 부정 시그널 합
    weighted_components: dict[str, float] = field(default_factory=dict)
    explanation: str = ""  # 점수 산정 이유 (XAI)


@dataclass
class Candidate:
    """파이프라인을 흐르는 핵심 데이터 단위 (댓글)"""

    id: str
    title: str
    content: str
    author: AuthorInfo
    created_at: datetime
    like_count: int
    category: str = "general"
    conversation_id: str | None = None
    is_deleted: bool = False
    is_slop: bool = False

    # Pipeline Stages를 거치며 채워짐
    features: CandidateFeatures = field(default_factory=CandidateFeatures)
    score: CandidateScore = field(default_factory=CandidateScore)
    metadata: dict[str, Any] = field(default_factory=dict)

    # 최종 선택 여부
    is_selected: bool = False
    selection_reason: str = ""
