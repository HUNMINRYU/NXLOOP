"""챗봇 서비스 단위 테스트 (의도 감지·카드 링크 안내)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.chatbot_service import ChatbotService


@pytest.fixture
def chatbot_service():
    """Gemini/RAG 목으로 챗봇 서비스 생성."""
    return ChatbotService(
        gemini_client=MagicMock(),
        rag_client=MagicMock(),
    )


def test_detect_intent_link_pricing(chatbot_service: ChatbotService) -> None:
    """요금/가격/요금제 의도 시 /pricing 카드 반환."""
    for msg in ["요금이 얼마예요?", "가격표 보여줘", "요금제 알려줘", "플랜 확인하고 싶어요"]:
        card = chatbot_service._detect_intent_link(msg)
        assert card is not None
        assert card.get("action") == "/pricing"
        assert "요금" in card.get("title", "") or "요금제" in card.get("title", "")


def test_detect_intent_link_login(chatbot_service: ChatbotService) -> None:
    """로그인 의도 시 /login 카드 반환."""
    card = chatbot_service._detect_intent_link("로그인 하고 싶어요")
    assert card is not None
    assert card.get("action") == "/login"


def test_detect_intent_link_signup(chatbot_service: ChatbotService) -> None:
    """회원가입 의도 시 /signup 카드 반환."""
    card = chatbot_service._detect_intent_link("회원가입 할게요")
    assert card is not None
    assert card.get("action") == "/signup"


def test_detect_intent_link_pipeline(chatbot_service: ChatbotService) -> None:
    """파이프라인/실행 의도 시 /pipeline 카드 반환."""
    card = chatbot_service._detect_intent_link("파이프라인 실행해줘")
    assert card is not None
    assert card.get("action") == "/pipeline"


def test_detect_intent_link_insights(chatbot_service: ChatbotService) -> None:
    """인사이트/대시보드 의도 시 /insights 카드 반환."""
    card = chatbot_service._detect_intent_link("인사이트 보여줘")
    assert card is not None
    assert card.get("action") == "/insights"


def test_detect_intent_link_home(chatbot_service: ChatbotService) -> None:
    """홈/메인 의도 시 / 카드 반환."""
    card = chatbot_service._detect_intent_link("홈으로 가고 싶어")
    assert card is not None
    assert card.get("action") == "/"


def test_detect_intent_link_no_match(chatbot_service: ChatbotService) -> None:
    """의도 매칭 없으면 None."""
    assert chatbot_service._detect_intent_link("썸네일 어떻게 만들죠?") is None
    assert chatbot_service._detect_intent_link("") is None


def test_sanitize_card_preserves_action_and_url(chatbot_service: ChatbotService) -> None:
    """카드 정제 시 action/url 유지."""
    card = {
        "title": "테스트",
        "bullets": ["항목1"],
        "cta": "이동",
        "action": "/pricing",
        "url": "https://example.com",
    }
    out = chatbot_service._sanitize_card(card)
    assert out is not None
    assert out.get("action") == "/pricing"
    assert out.get("url") == "https://example.com"
