"""
알림 서비스 (Slack + 이메일)
- Slack: requests.post 로 실제 발송
- 이메일: 현재는 로그 전용 (추후 SMTP/Resend 연동 시 _do_send 교체)
"""

from __future__ import annotations

import requests

from config.settings import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# 테스트 환경 이메일 allowlist (설정에서 파싱)
_EMAIL_ALLOWLIST: set[str] = settings.test_email_allowlist


# ── Slack ────────────────────────────────────────────────

def send_slack_notification(message: str) -> None:
    """Slack Incoming Webhook 으로 메시지를 전송합니다.

    - SLACK_WEBHOOK_URL 이 비어 있으면 skip
    - 전송 실패 시 로그만 남기고 예외를 전파하지 않음
    """
    url = settings.slack_webhook_url
    if not url:
        logger.debug("Slack webhook URL이 설정되지 않아 알림을 건너뜁니다.")
        return

    try:
        resp = requests.post(url, json={"text": message}, timeout=5)
        if resp.status_code != 200:
            logger.warning(
                "Slack 알림 전송 실패: status=%s body=%s",
                resp.status_code,
                resp.text[:200],
            )
        else:
            logger.info("Slack 알림 전송 완료")
    except Exception as e:
        logger.warning("Slack 알림 전송 중 오류: %s", e)


# ── Email ────────────────────────────────────────────────

def send_email(to: str, subject: str, body: str) -> None:
    """이메일을 발송합니다 (현재는 로그 전용).

    테스트 환경(ENV != production):
      - to 가 TEST_EMAIL_ALLOWLIST 에 없으면 발송 건너뜀
      - subject 에 [TEST] 접두어, body 에 경고 문구 추가
    """
    # 테스트 환경 가드
    if settings.env != "production":
        if to not in _EMAIL_ALLOWLIST:
            logger.info(
                "Skip email (test env, not in allowlist): to=%s", to
            )
            return

        subject = f"[TEST] {subject}"
        body = (
            "⚠️ This is a TEST notification.\n\n"
            + body
        )

    # 실제 발송 (현재 로그 전용 — 추후 _do_send 로 교체)
    _do_send(to, subject, body)


def _do_send(to: str, subject: str, body: str) -> None:
    """실제 메일 전송 로직.

    현재는 로그로만 기록합니다.
    SMTP/Resend 등을 연동할 때 이 함수만 교체하면 됩니다.
    """
    logger.info(
        "📧 Email notification (log-only)\n"
        "  To: %s\n"
        "  Subject: %s\n"
        "  Body:\n%s",
        to,
        subject,
        body,
    )
