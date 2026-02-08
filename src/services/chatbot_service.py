"""
챗봇 서비스
"""

from __future__ import annotations

import json
import re
from threading import Lock
from typing import Any
from uuid import uuid4

from config.products import get_product_catalog
from core.interfaces.ai_service import IMarketingAIService
from core.interfaces.chatbot import IRAGClient
from core.models.chatbot import ChatSession
from core.prompts import (
    prompt_registry,
)
from utils.logger import log_error, log_info, log_llm_fail, log_llm_request, log_llm_response


class ChatbotService:
    """챗봇 비즈니스 로직"""

    def __init__(
        self, gemini_client: IMarketingAIService, rag_client: IRAGClient
    ) -> None:
        self._gemini_client = gemini_client
        self._rag_client = rag_client
        self._sessions: dict[str, ChatSession] = {}
        self._lock = Lock()

    async def generate_reply(
        self,
        message: str,
        session_id: str | None = None,
        data_store_id: str | None = None,
    ) -> dict:
        text = message.strip()
        if not text:
            return {
                "session_id": session_id or "",
                "message": "메시지를 입력해 주세요.",
                "card": None,
                "sources": [],
            }

        session = self._get_or_create_session(session_id)
        
        # 1. 쿼리 최적화
        search_query = await self._generate_search_query(session, text)
        session.add_message("user", text)

        rag_results = []
        use_grounding = False
        sources = []

        if search_query:
            # Parallel Execution possible, but keeping sequential for now
            rag_results = await self._rag_client.search(
                search_query,
                max_results=5,
                data_store_id=data_store_id,
            )
            sources = self._sanitize_sources(rag_results)
            use_grounding = not rag_results
        
        product = self._detect_product(text)
        
        prompt = self._build_prompt(
            message=text,
            session=session,
            product=product,
            rag_results=rag_results,
        )
        log_llm_request("챗봇 응답", f"메시지 {len(text)}자, Query={search_query}")
        store_tag = (data_store_id or "").strip()
        store_tag = store_tag[-8:] if store_tag else "none"
        log_info(f"RAG used: results={len(rag_results)} sources={len(sources)} store={store_tag}")

        try:
            # .env GEMINI_TEXT_MODEL 사용 (클라이언트 기본값)
            raw_response = await self._gemini_client.generate_content_async(
                prompt=prompt,
                temperature=0.4,
                use_grounding=use_grounding,
            )
            
            log_llm_response("챗봇 응답", f"응답 {len(raw_response or '')}자")
        except Exception as e:
            log_llm_fail("챗봇 응답", str(e))
            log_error(f"챗봇 응답 생성 실패: {e}")
            raw_response = "죄송합니다. 현재 응답을 생성할 수 없습니다."

        parsed = self._parse_json_output(raw_response)
        answer = parsed.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            answer = raw_response.strip()

        card = parsed.get("card") if isinstance(parsed, dict) else None
        card = None if not isinstance(card, dict) else self._sanitize_card(card)

        session.add_message("ai", answer)

        return {
            "session_id": session.session_id,
            "message": answer,
            "card": card,
            "sources": sources,
        }

    def _sanitize_sources(self, rag_results: list[dict[str, Any]]) -> list[dict[str, str]]:
        """프론트 표시용 sources 정제.

        - 상위 3개만
        - url/title 기반 중복 제거
        - title/snippet 길이 제한
        """

        if not rag_results:
            return []

        sources: list[dict[str, str]] = []
        seen: set[str] = set()

        for item in rag_results:
            if not isinstance(item, dict):
                continue

            title_raw = item.get("title") or ""
            snippet_raw = item.get("snippet") or ""
            url_raw = item.get("url") or ""

            title = str(title_raw).strip()[:100]
            snippet = str(snippet_raw).strip()[:200]
            url = str(url_raw).strip()[:500]

            if not title and not snippet:
                continue

            key = url or f"{title}|{snippet}"
            if key in seen:
                continue
            seen.add(key)

            payload: dict[str, str] = {"title": title or "Untitled"}
            if snippet:
                payload["snippet"] = snippet
            if url:
                payload["url"] = url

            sources.append(payload)
            if len(sources) >= 3:
                break

        return sources

    def _get_or_create_session(self, session_id: str | None) -> ChatSession:
        with self._lock:
            if session_id and session_id in self._sessions:
                return self._sessions[session_id]
            new_id = session_id or str(uuid4())
            session = ChatSession(session_id=new_id)
            self._sessions[new_id] = session
            return session

    def _detect_product(self, message: str) -> dict[str, Any] | None:
        for product in get_product_catalog():
            if product.name in message:
                return product.model_dump()
        return None

    def _build_prompt(
        self,
        message: str,
        session: ChatSession,
        product: dict[str, Any] | None,
        rag_results: list[dict[str, Any]],
    ) -> str:
        recent_messages = session.messages[-6:]
        history_lines = "\n".join(
            f"- {msg.role}: {msg.content}" for msg in recent_messages
        )
        product_names = [p.name for p in get_product_catalog()]

        rag_lines = []
        for idx, item in enumerate(rag_results, start=1):
            rag_lines.append(
                f"{idx}) 제목: {item.get('title', '')}\n"
                f"   링크: {item.get('url', '')}\n"
                f"   요약: {item.get('snippet', '')}"
            )

        rag_block = "\n".join(rag_lines) if rag_lines else "검색 결과 없음"
        product_block = (
            json.dumps(product, ensure_ascii=False, indent=2) if product else "없음"
        )

        return prompt_registry.get("chatbot.reply").render(
            message=message,
            history_lines=history_lines,
            product_names_json=json.dumps(product_names, ensure_ascii=False),
            product_block=product_block,
            rag_block=rag_block,
        )

    def _parse_json_output(self, text: str) -> dict[str, Any]:
        cleaned = re.sub(r"```json\s*", "", text)
        cleaned = re.sub(r"```\s*$", "", cleaned)
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", cleaned)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    return {}
        return {}

    def _sanitize_card(self, card: dict[str, Any]) -> dict[str, Any] | None:
        title = card.get("title")
        bullets = card.get("bullets")
        cta = card.get("cta")

        if not isinstance(title, str) or not title.strip():
            return None
        if not isinstance(bullets, list):
            return None

        cleaned_bullets = [str(b).strip() for b in bullets if str(b).strip()]
        if not cleaned_bullets:
            return None

        cleaned = {
            "title": title.strip(),
            "bullets": cleaned_bullets,
        }
        if isinstance(cta, str) and cta.strip():
            cleaned["cta"] = cta.strip()
        return cleaned

    async def _generate_search_query(
        self,
        session: ChatSession,
        current_message: str,
    ) -> str:
        """대화 이력을 기반으로 검색 쿼리 최적화 (Gemini 1.5 Flash 사용)"""
        recent_messages = session.messages[-4:]  # 최근 4턴만 참조
        history_lines = "\n".join(
            f"- {msg.role}: {msg.content}" for msg in recent_messages
        )
        
        prompt = prompt_registry.get("chatbot.query_gen").render(
            history_lines=history_lines,
            message=current_message,
        )

        try:
            # .env GEMINI_TEXT_MODEL 사용 (클라이언트 기본값)
            query = await self._gemini_client.generate_text_async(
                prompt=prompt,
                temperature=0.1,  # 창의성 최소화
                max_retries=2,
            )
            query = query.strip()
            # NO_SEARCH 처리
            if "NO_SEARCH" in query:
                return ""
            return query
        except Exception as e:
            log_error(f"쿼리 생성 실패: {e}")
            return current_message  # 실패 시 원본 메시지 사용

    async def generate_reply_stream(
        self,
        message: str,
        session_id: str | None = None,
        data_store_id: str | None = None,
    ):
        """SSE 스트리밍 응답 생성"""
        import json

        text = message.strip()
        if not text:
            yield f"data: {json.dumps({'error': '메시지를 입력해 주세요.'}, ensure_ascii=False)}\n\n"
            return

        session = self._get_or_create_session(session_id)
        
        # 1. 쿼리 최적화 (검색 전 단계)
        yield f"data: {json.dumps({'step': 'searching', 'message': '질문을 분석하고 있습니다...'}, ensure_ascii=False)}\n\n"
        
        search_query = await self._generate_search_query(session, text)
        session.add_message("user", text) # 쿼리 생성 후 이력에 추가

        rag_results = []
        use_grounding = False
        sources = []

        if search_query:
            # 2. 문서 검색
            yield f"data: {json.dumps({'step': 'searching', 'message': f'🔍 검색: {search_query}'}, ensure_ascii=False)}\n\n"
            
            rag_results = await self._rag_client.search(
                search_query,
                max_results=5,
                data_store_id=data_store_id,
            )
            sources = self._sanitize_sources(rag_results)
            use_grounding = not rag_results
        else:
             # 검색 불필요 (인사말 등)
             pass

        product = self._detect_product(text)

        # 3. 답변 생성
        yield f"data: {json.dumps({'step': 'generating', 'message': '답변을 생성하고 있습니다...', 'sources': sources}, ensure_ascii=False)}\n\n"

        prompt = self._build_prompt(
            message=text,
            session=session,
            product=product,
            rag_results=rag_results,
        )
        log_llm_request("챗봇 스트리밍", f"메시지 {len(text)}자, Query={search_query}")

        try:
            full_response = []
            # .env GEMINI_TEXT_MODEL 사용 (클라이언트 기본값)
            async for chunk in self._gemini_client.generate_content_stream(
                prompt=prompt,
                temperature=0.4,
                use_grounding=use_grounding,
            ):
                if chunk:
                    full_response.append(chunk)
                    yield f"data: {json.dumps({'token': chunk}, ensure_ascii=False)}\n\n"
            
            # 4. 완료 처리
            full_text = "".join(full_response)
            log_llm_response("챗봇 스트리밍", f"응답 {len(full_text)}자")
            
            parsed = self._parse_json_output(full_text)
            answer = parsed.get("answer")
            if not isinstance(answer, str) or not answer.strip():
                answer = full_text.strip()

            card = parsed.get("card") if isinstance(parsed, dict) else None
            card = None if not isinstance(card, dict) else self._sanitize_card(card)

            session.add_message("ai", answer)

            yield f"data: {json.dumps({'step': 'done', 'full_text': answer, 'card': card, 'session_id': session.session_id}, ensure_ascii=False)}\n\n"

        except Exception as e:
            log_llm_fail("챗봇 스트리밍", str(e))
            log_error(f"챗봇 스트리밍 실패: {e}")
            yield f"data: {json.dumps({'error': '죄송합니다. 응답 생성 중 오류가 발생했습니다.'}, ensure_ascii=False)}\n\n"
