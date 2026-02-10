"""챗봇 서비스 단위 테스트 (의도 감지·카드 링크 안내)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from services.chatbot_service import ChatbotService


@pytest.mark.asyncio
async def test_generate_reply_intent_pricing_no_llm(chatbot_service: ChatbotService) -> None:
    """요금제 의도 시 LLM 호출 없이 고정 메시지+카드 즉시 반환."""
    result = await chatbot_service.generate_reply("요금제 알려줘")
    assert result["message"] == "요금제 페이지로 안내해 드릴게요."
    assert result["card"] is not None
    assert result["card"].get("action") == "/pricing"
    assert result["sources"] == []
    # LLM 미호출 검증
    chatbot_service._gemini_client.generate_content_async.assert_not_called()


@pytest.mark.asyncio
async def test_generate_reply_intent_create_choices_no_llm(chatbot_service: ChatbotService) -> None:
    """생성 의도 시 LLM 호출 없이 고정 메시지+선택지 카드 즉시 반환."""
    result = await chatbot_service.generate_reply("생성하러 갈게")
    assert result["message"] == "어디로 가실지 아래에서 골라 주세요."
    assert result["card"] is not None
    assert result["card"].get("title") == "어디로 가시겠어요?"
    actions = result["card"].get("actions")
    assert isinstance(actions, list) and len(actions) == 3
    assert result["sources"] == []
    chatbot_service._gemini_client.generate_content_async.assert_not_called()


@pytest.mark.asyncio
async def test_generate_reply_no_intent_calls_llm(chatbot_service: ChatbotService) -> None:
    """의도 매칭 없으면 RAG/LLM 경로로 진행 (generate_content_async 호출됨)."""
    chatbot_service._gemini_client.generate_text_async = AsyncMock(return_value="오늘 날씨")
    chatbot_service._gemini_client.generate_content_async = AsyncMock(
        return_value='{"answer": "테스트 답변입니다.", "card": null}'
    )
    chatbot_service._rag_client.search = AsyncMock(return_value=[])
    await chatbot_service.generate_reply("오늘 날씨 어때?")
    chatbot_service._gemini_client.generate_content_async.assert_called_once()


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
    """파이프라인/실행 의도 시 /pipeline/create 카드 반환."""
    card = chatbot_service._detect_intent_link("파이프라인 실행해줘")
    assert card is not None
    assert card.get("action") == "/pipeline/create"


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


def test_detect_intent_link_create_choices(chatbot_service: ChatbotService) -> None:
    """생성 의도 시 자동화/썸네일/비디오 선택지 카드(actions) 반환."""
    card = chatbot_service._detect_intent_link("생성하러 갈게")
    assert card is not None
    assert card.get("title") == "어디로 가시겠어요?"
    actions = card.get("actions")
    assert isinstance(actions, list) and len(actions) == 3
    labels = [a.get("label") for a in actions]
    paths = [a.get("action") for a in actions]
    assert "자동화하러 가기" in labels
    assert "썸네일만 생성" in labels
    assert "비디오만 생성" in labels
    assert "/pipeline/create" in paths
    assert "/pipeline/thumbnail" in paths
    assert "/pipeline/video" in paths


def test_detect_intent_link_no_match(chatbot_service: ChatbotService) -> None:
    """의도 매칭 없으면 None."""
    assert chatbot_service._detect_intent_link("오늘 날씨 어때?") is None
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


def test_sanitize_card_preserves_actions(chatbot_service: ChatbotService) -> None:
    """카드 정제 시 다중 선택지(actions) 유지."""
    card = {
        "title": "어디로 가시겠어요?",
        "bullets": ["자동화", "썸네일", "비디오"],
        "actions": [
            {"label": "자동화", "action": "/pipeline/create"},
            {"label": "썸네일", "action": "/pipeline/thumbnail"},
            {"label": "비디오", "url": "https://example.com"},
        ],
    }
    out = chatbot_service._sanitize_card(card)
    assert out is not None
    actions = out.get("actions")
    assert isinstance(actions, list) and len(actions) == 3
    assert actions[0]["label"] == "자동화" and actions[0]["action"] == "/pipeline/create"
    assert actions[1]["label"] == "썸네일" and actions[1]["action"] == "/pipeline/thumbnail"
    assert actions[2]["label"] == "비디오" and actions[2]["url"] == "https://example.com"
