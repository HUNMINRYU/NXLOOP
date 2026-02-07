"""
환경변수 기반 설정 관리
Pydantic Settings를 사용하여 안전하게 API 키 및 설정 관리

Note: YouTube/Gemini는 Vertex AI를 사용하므로 GCP 서비스 계정으로 통합 인증
"""

import json
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from utils.logger import get_logger

logger = get_logger(__name__)

# 프로젝트 루트 디렉토리 설정 (src/config/settings.py 기준 2단계 상위)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

AI_MODEL_RATIONALE = {
    "gemini-3-pro-preview": {
        "선택 이유": "텍스트 생성 + 멀티모달 분석 최적화",
        "대안 검토": ["GPT-4", "Claude"],
        "채택 근거": "GCP 네이티브 통합, 비용 효율성",
    },
    "veo-3.1-fast-generate-001": {
        "선택 이유": "빠른 영상 생성 속도",
        "채택 근거": "마케팅 캠페인의 시간 민감성 대응",
    },
}


class GCPSettings(BaseSettings):
    """GCP 설정 (Vertex AI 통합 인증)"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    project_id: str = Field(
        ...,
        validation_alias=AliasChoices("GOOGLE_CLOUD_PROJECT_ID", "GOOGLE_PROJECT_ID"),
    )
    location: str = Field(
        default="us-central1",
        validation_alias=AliasChoices("GOOGLE_CLOUD_LOCATION", "VERTEX_LOCATION"),
    )
    gcs_bucket_name: str | None = Field(
        default=None, validation_alias="GCS_BUCKET_NAME"
    )
    credentials_path: str | None = Field(
        default=None, validation_alias="GOOGLE_APPLICATION_CREDENTIALS"
    )
    data_store_id: str | None = Field(default=None, validation_alias="DATA_STORE_ID")

    # Vertex AI 통합 API 키 (YouTube, Gemini 공용)
    google_api_key: SecretStr = Field(..., validation_alias="GOOGLE_API_KEY")


class NaverSettings(BaseSettings):
    """네이버 API 설정"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    client_id: SecretStr = Field(..., validation_alias="NAVER_CLIENT_ID")
    client_secret: SecretStr = Field(..., validation_alias="NAVER_CLIENT_SECRET")


class AIModelSettings(BaseSettings):
    """AI 모델 설정"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    gemini_text_model: str = Field(
        default="gemini-3-pro-preview", validation_alias="GEMINI_TEXT_MODEL"
    )
    gemini_image_model: str = Field(
        default="gemini-3-pro-image-preview", validation_alias="GEMINI_IMAGE_MODEL"
    )
    veo_model_id: str = Field(
        default="veo-3.1-fast-generate-001", validation_alias="VEO_MODEL_ID"
    )


class NotionSettings(BaseSettings):
    """Notion API 설정"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    api_key: SecretStr | None = Field(default=None, validation_alias="NOTION_API_KEY")
    database_id: str | None = Field(default=None, validation_alias="NOTION_DATABASE_ID")


class PipelineSettings(BaseSettings):
    """파이프라인 다양성/스코어링 설정"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    author_diversity_decay: float = Field(
        default=0.7, validation_alias="PIPELINE_AUTHOR_DIVERSITY_DECAY"
    )
    author_diversity_floor: float = Field(
        default=0.3, validation_alias="PIPELINE_AUTHOR_DIVERSITY_FLOOR"
    )
    topic_diversity_decay: float = Field(
        default=0.8, validation_alias="PIPELINE_TOPIC_DIVERSITY_DECAY"
    )
    topic_diversity_floor: float = Field(
        default=0.5, validation_alias="PIPELINE_TOPIC_DIVERSITY_FLOOR"
    )
    use_multi_diversity: bool = Field(
        default=False, validation_alias="PIPELINE_USE_MULTI_DIVERSITY"
    )
    reranking_alpha: float = Field(
        default=0.7, validation_alias="PIPELINE_RERANKING_ALPHA"
    )
    use_bloom_filter: bool = Field(
        default=False, validation_alias="PIPELINE_USE_BLOOM_FILTER"
    )


class AppSettings(BaseSettings):
    """애플리케이션 전체 설정"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "제네시스코리아 스튜디오"
    debug: bool = Field(default=False, validation_alias="DEBUG")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    output_dir: str = Field(default="outputs", validation_alias="OUTPUT_DIR")
    stripe_publishable_key: str = Field(
        default="",
        validation_alias="STRIPE_PUBLISHABLE_KEY",
    )
    stripe_secret_key: SecretStr | None = Field(
        default=None,
        validation_alias="STRIPE_SECRET_KEY",
    )
    stripe_webhook_secret: SecretStr | None = Field(
        default=None,
        validation_alias="STRIPE_WEBHOOK_SECRET",
    )
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/auth.db",
        validation_alias="DATABASE_URL",
    )
    jwt_secret: str = Field(default="dev-secret", validation_alias="JWT_SECRET")
    jwt_expire_hours: int = Field(default=24, validation_alias="JWT_EXPIRE_HOURS")
    app_url: str = Field(default="http://localhost:8000", validation_alias="APP_URL")
    scheduler_service_account: str = Field(
        default="", validation_alias="SCHEDULER_SERVICE_ACCOUNT"
    )
    scheduler_location: str = Field(
        default="asia-northeast3", validation_alias="SCHEDULER_LOCATION"
    )
    brand_banned_keywords_raw: str = Field(
        default="",
        validation_alias="BRAND_BANNED_KEYWORDS",
    )
    rag_data_stores_raw: str = Field(
        default="{}",
        validation_alias="RAG_DATA_STORES",
    )
    rag_ingestion_max_retries: int = Field(
        default=3,
        validation_alias="RAG_INGESTION_MAX_RETRIES",
    )
    rag_ingestion_backoff_seconds: float = Field(
        default=0.5,
        validation_alias="RAG_INGESTION_BACKOFF_SECONDS",
    )
    rag_ingestion_jitter_seconds: float = Field(
        default=0.1,
        validation_alias="RAG_INGESTION_JITTER_SECONDS",
    )

    # ── 알림 설정 ──
    env: str = Field(default="development", validation_alias="ENV")
    slack_webhook_url: str = Field(default="", validation_alias="SLACK_WEBHOOK_URL")
    test_email_allowlist_raw: str = Field(
        default="", validation_alias="TEST_EMAIL_ALLOWLIST"
    )


class Settings:
    """통합 설정 클래스"""

    def __init__(self) -> None:
        self.app = AppSettings()
        self.gcp = GCPSettings()  # type: ignore[call-arg]
        self.naver = NaverSettings()  # type: ignore[call-arg]
        self.notion = NotionSettings()
        self.models = AIModelSettings()
        self.pipeline = PipelineSettings()

    @property
    def stripe_publishable_key(self) -> str:
        """Stripe Publishable Key 반환"""
        return self.app.stripe_publishable_key

    @property
    def stripe_secret_key(self) -> str:
        """Stripe Secret Key 반환"""
        return (
            self.app.stripe_secret_key.get_secret_value()
            if self.app.stripe_secret_key
            else ""
        )

    @property
    def stripe_webhook_secret(self) -> str:
        """Stripe Webhook Secret 반환"""
        return (
            self.app.stripe_webhook_secret.get_secret_value()
            if self.app.stripe_webhook_secret
            else ""
        )

    @property
    def google_api_key(self) -> str:
        """Google API 키 반환 (YouTube, Gemini 공용)"""
        return self.gcp.google_api_key.get_secret_value()

    @property
    def notion_api_key(self) -> str:
        """Notion API 키 반환"""
        return self.notion.api_key.get_secret_value() if self.notion.api_key else ""

    @property
    def notion_database_id(self) -> str:
        """Notion Database ID 반환"""
        return self.notion.database_id or ""

    @property
    def brand_banned_keywords(self) -> list[str]:
        raw = self.app.brand_banned_keywords_raw
        if not raw:
            return []
        return [item.strip() for item in raw.split(",") if item.strip()]

    @property
    def rag_data_stores(self) -> dict[str, str]:
        raw = self.app.rag_data_stores_raw
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
        return {}

    @property
    def env(self) -> str:
        """실행 환경 (development / test / production)"""
        return self.app.env

    @property
    def slack_webhook_url(self) -> str:
        """Slack Incoming Webhook URL"""
        return self.app.slack_webhook_url

    @property
    def test_email_allowlist(self) -> set[str]:
        """테스트 환경에서 이메일 발송을 허용할 주소 목록"""
        raw = self.app.test_email_allowlist_raw
        if not raw:
            return set()
        return {e.strip() for e in raw.split(",") if e.strip()}

    def has_notion_api_key(self) -> bool:
        """Notion API 키 설정 여부"""
        return bool(self.notion.api_key and self.notion.api_key.get_secret_value())

    def get_missing_required_settings(self) -> list[str]:
        """필수 설정 누락 항목 반환"""
        missing = []
        if not self.gcp.project_id:
            missing.append("GOOGLE_CLOUD_PROJECT_ID")
        if not self.gcp.google_api_key.get_secret_value():
            missing.append("GOOGLE_API_KEY")
        if not self.naver.client_id.get_secret_value():
            missing.append("NAVER_CLIENT_ID")
        if not self.naver.client_secret.get_secret_value():
            missing.append("NAVER_CLIENT_SECRET")
        return missing

    def setup_environment(self) -> None:
        """GCP 환경변수 설정 (Vertex AI용)"""
        import os

        os.environ["GOOGLE_CLOUD_PROJECT"] = self.gcp.project_id
        os.environ["GOOGLE_CLOUD_LOCATION"] = self.gcp.location
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

        if self.gcp.credentials_path:
            path = Path(self.gcp.credentials_path)

            # 상대 경로인 경우 프로젝트 루트와 결합하여 절대 경로 생성
            if not path.is_absolute():
                credentials_path = (PROJECT_ROOT / path).resolve()
            else:
                credentials_path = path

            if credentials_path.exists():
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path)
                logger.info(f"GCP 인증 설정 완료 (로컬 경로): {credentials_path.name}")
            else:
                logger.warning(f"GCP 인증 파일을 찾을 수 없습니다: {credentials_path} ")
                if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
                    del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
        else:
            logger.info("GCP 인증 파일 경로가 설정되지 않았습니다. ADC를 사용합니다.")


@lru_cache
def get_settings() -> Settings:
    """캐시된 설정 인스턴스 반환"""
    return Settings()
