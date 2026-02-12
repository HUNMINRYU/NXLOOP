from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


KST = timezone(timedelta(hours=9))


def now_kst() -> datetime:
    return datetime.now(KST)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="editor", nullable=False)
    role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.id"), nullable=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Stripe 구독 관련 필드
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    tier: Mapped[str] = mapped_column(
        String(20), default="FREE", nullable=False, server_default="FREE"
    )
    subscription_status: Mapped[str] = mapped_column(
        String(20), default="none", nullable=False, server_default="none"
    )
    subscription_end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_kst, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_kst,
        onupdate=now_kst,
        nullable=False,
    )

    team = relationship("Team", back_populates="members")
    role_ref = relationship("Role", back_populates="users")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_kst, nullable=False
    )

    users = relationship("User", back_populates="role_ref")


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_kst, nullable=False
    )

    members = relationship("User", back_populates="team")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=True)
    meta_json: Mapped[str] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_kst, nullable=False
    )


class PipelineTask(Base):
    """Cloud Run 다중 인스턴스에서도 안정적으로 조회 가능한 파이프라인 상태/결과 저장."""

    __tablename__ = "pipeline_tasks"

    task_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    product_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    message: Mapped[str] = mapped_column(String(500), nullable=False, default="")

    # JSON 직렬화된 상태 스냅샷(프론트 응답과 동일한 형태를 저장)
    status_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_kst, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_kst,
        onupdate=now_kst,
        nullable=False,
        index=True,
    )

    @staticmethod
    def dumps(payload) -> str:
        def _default(obj):
            # 파이프라인 결과/상태는 다양한 타입을 포함할 수 있어 JSON 직렬화 방어가 필요합니다.
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            if isinstance(obj, UUID):
                return str(obj)
            if isinstance(obj, Decimal):
                # 금액/정확도가 중요한 값이 있을 수 있어 문자열로 보존
                return str(obj)
            if isinstance(obj, Enum):
                return obj.value
            # Pydantic v2/v1 객체 방어 (가능하면 dict 형태로 저장)
            if hasattr(obj, "model_dump"):
                return obj.model_dump()
            if hasattr(obj, "dict"):
                return obj.dict()
            return str(obj)

        return json.dumps(
            payload or {},
            ensure_ascii=False,
            separators=(",", ":"),
            default=_default,
        )


class PipelineSchedule(Base):
    __tablename__ = "pipeline_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Cloud Scheduler 정보
    gcp_job_id: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(50), default="Asia/Seoul", nullable=False
    )

    # 파이프라인 설정
    product_name: Mapped[str] = mapped_column(String(100), nullable=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False)

    # 상태
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_executed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_execution_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Optimistic Locking
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # 메타데이터
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_kst, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_kst,
        onupdate=now_kst,
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # Soft delete

    creator = relationship("User", foreign_keys=[created_by])


class UserProfileModel(Base):
    """파이프라인 사용자 선호도 프로필"""

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    preferences_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    topic_affinities_json: Mapped[str] = mapped_column(
        Text, default="{}", nullable=False
    )
    interaction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_kst,
        onupdate=now_kst,
        nullable=False,
    )


class CTRFeedback(Base):
    """CTR 예측 vs 실제 성과 피드백"""

    __tablename__ = "ctr_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(String(200), nullable=False)
    predicted_ctr: Mapped[str] = mapped_column(String(20), nullable=False)
    actual_ctr: Mapped[str | None] = mapped_column(String(20), nullable=True)
    error: Mapped[str | None] = mapped_column(String(20), nullable=True)
    model_version: Mapped[str] = mapped_column(String(50), default="v1", nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_kst, nullable=False
    )


class ModelEvalReport(Base):
    """오프라인 모델 평가 리포트 요약(운영 조회/Notion 링크용).

    원본(JSON/MD)은 GCS에 아카이브하고, DB에는 요약 메트릭만 저장합니다.
    """

    __tablename__ = "model_eval_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # 핵심 요약/메트릭(간단 조회용). 구조 변경이 잦으므로 JSON(Text)로 둔다.
    dataset_counts_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    cls_metrics_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    reg_metrics_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    baseline_metrics_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    # 아카이브/외부 링크
    artifact_gcs_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notion_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kst, nullable=False)


class BrandKit(Base):
    """일관된 브랜드 정체성을 위한 브랜드 킷"""

    __tablename__ = "brand_kits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    primary_color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    secondary_color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    font_style: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tone_and_voice: Mapped[str | None] = mapped_column(String(255), nullable=True)
    visual_vibes_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    logo_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_kst, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_kst,
        onupdate=now_kst,
        nullable=False,
    )


class UserSession(Base):
    """서버 세션(쿠키 기반 인증) 저장 테이블."""

    __tablename__ = "user_sessions"

    # UUID 문자열(쿠키에 저장될 세션 ID)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kst, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User")


class UserDailyChatUsage(Base):
    """FREE tier 로그인 사용자 일일 챗봇 메시지 사용량 (10회/일 제한용)."""

    __tablename__ = "user_daily_chat_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    usage_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)  # KST 기준 날짜
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "usage_date", name="uq_user_daily_chat_usage"),)


class CTRRankerRun(Base):
    """CTR Ranker 실행 단위.

    승인 워크플로우에서 "이번 실행(run)에서 어떤 후보를 보여줬고 무엇을 채택했는지"를
    재현 가능하게 남기는 것이 목적입니다.
    """

    __tablename__ = "ctr_ranker_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(50), default="youtube", nullable=False)

    # 원본/리포트 위치(로컬 경로 또는 GCS object path). 운영에서는 GCS가 권장됩니다.
    raw_dataset_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    topk_csv_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    report_json_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 요약 메트릭(예: ndcg@k 등) 저장. UI에서 "성과가 있었는지"를 빠르게 보여줄 수 있습니다.
    metrics_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kst, nullable=False)

    candidates = relationship(
        "CTRRankerCandidate",
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    approval = relationship(
        "CTRRankerApproval",
        back_populates="run",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class CTRRankerCandidate(Base):
    """run에서 노출되는 후보(제목+썸네일 세트) 단위."""

    __tablename__ = "ctr_ranker_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("ctr_ranker_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 원본 식별자(YouTube video_id 등)
    video_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Before/After topK 비교를 위해 둘 다 저장 (스케일이 달라 직접 비교는 금지).
    baseline_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    baseline_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    after_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    after_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    proxy_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    meta_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kst, nullable=False)

    run = relationship("CTRRankerRun", back_populates="candidates")
    approvals = relationship("CTRRankerApproval", back_populates="candidate")

    __table_args__ = (
        # 같은 run 안에서 동일 video_id가 중복 저장되는 실수를 방지 (video_id 없는 경우는 허용)
        UniqueConstraint("run_id", "video_id", name="uq_ctr_ranker_candidates_run_video"),
    )


class CTRRankerApproval(Base):
    """run 단위 채택 결과 (제품당 1개 승인)."""

    __tablename__ = "ctr_ranker_approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("ctr_ranker_runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("ctr_ranker_candidates.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    approved_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kst, nullable=False)

    run = relationship("CTRRankerRun", back_populates="approval")
    candidate = relationship("CTRRankerCandidate", back_populates="approvals")
    approved_by = relationship("User")
