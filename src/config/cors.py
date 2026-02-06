"""CORS 설정 유틸리티.

Cloud Run 배포 환경에서는 환경변수 누락/빈값 때문에 CORS가 완전히 차단되는 경우가 있다.
브라우저에서의 차단은 기능 장애로 직결되므로, Cloud Run에서는 기본값을 보다 관대하게 둔다.
"""

from __future__ import annotations


LOCAL_DEV_DEFAULT_ORIGINS: list[str] = ["http://localhost:3000"]
"""로컬 개발 기본 Origin 목록."""


def resolve_cors_origins(
    cors_origins_env: str | None,
    *,
    is_cloud_run: bool,
) -> list[str]:
    """`CORS_ORIGINS` 환경변수를 파싱해 CORSMiddleware에 넣을 origin 목록을 반환한다.

    정책:
    - 값이 정상적으로 들어오면(쉼표 구분) 그대로 사용한다.
    - 값이 비어 있거나 파싱 결과가 빈 리스트면:
      - Cloud Run: `["*"]`로 fallback (allow_credentials=False 전제)
      - 로컬: `["http://localhost:3000"]`로 fallback
    """

    if cors_origins_env is None:
        return ["*"] if is_cloud_run else LOCAL_DEV_DEFAULT_ORIGINS

    parsed = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
    if parsed:
        return parsed

    return ["*"] if is_cloud_run else LOCAL_DEV_DEFAULT_ORIGINS

