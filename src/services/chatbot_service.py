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
from utils.logger import (
    log_error,
    log_info,
    log_llm_fail,
    log_llm_request,
    log_llm_response,
)

# 인사·간단 문구 즉시 응답 (챗봇 응답 속도 개선)
GREETING_PATTERNS = (
    "안녕",
    "반가워",
    "반갑습니다",
    "하이",
    "헬로",
    "hello",
    "hi",
    "뭐해",
    "뭐하세요",
)
GREETING_REPLY = (
    "반갑습니다! 숏폼 알고리즘과 콘텐츠 전략을 도와드리는 NEXLOOP AI예요. "
    "마케팅하시려는 제품이나 궁금한 점을 말씀해 주시면 바로 도와드릴게요."
)

# 사용자 의도 → 서비스 내 링크 안내 (의도 파악 후 카드로 안내)
# (키워드, path, title, bullets, cta, 즉시 응답용 메시지)
INTENT_LINKS: list[tuple[list[str], str, str, list[str], str, str]] = [
    (
        ["요금", "가격", "요금제", "플랜", "구독", "비용", "pricing", "가격표"],
        "/pricing",
        "요금제 안내",
        ["요금제와 플랜을 확인하실 수 있어요.", "가입 후 파이프라인·인사이트를 활용해 보세요."],
        "요금제 보기",
        "요금제 페이지로 안내해 드릴게요.",
    ),
    (
        ["로그인", "로그인 하", "로그인해", "로그인 해", "sign in", "login"],
        "/login",
        "로그인",
        ["로그인하면 저장된 프로젝트와 인사이트를 이어서 이용할 수 있어요."],
        "로그인하기",
        "로그인 페이지로 이동해 드릴게요.",
    ),
    (
        ["회원가입", "가입", "회원 가입", "sign up", "signup", "가입하기"],
        "/signup",
        "회원가입",
        ["무료로 시작할 수 있어요.", "가입 후 파이프라인과 인사이트를 바로 이용해 보세요."],
        "회원가입하기",
        "회원가입 페이지로 안내해 드릴게요.",
    ),
    (
        ["파이프라인", "파이프라인 실행", "실행", "분석", "파이프라인 돌", "실행해"],
        "/pipeline/create",
        "파이프라인 실행",
        ["YouTube·네이버 데이터로 인사이트를 추출할 수 있어요.", "실행 후 결과를 대시보드에서 확인하세요."],
        "파이프라인 보기",
        "파이프라인 실행 페이지로 안내해 드릴게요.",
    ),
    (
        ["인사이트", "대시보드", "결과", "분석 결과", "인사이트 보기", "대시보드 보기"],
        "/insights",
        "인사이트·대시보드",
        ["추출된 인사이트와 분석 결과를 한눈에 볼 수 있어요."],
        "인사이트 보기",
        "인사이트·대시보드로 안내해 드릴게요.",
    ),
    (
        ["홈", "메인", "처음", "홈으로", "main", "home"],
        "/",
        "홈",
        ["메인 페이지에서 서비스 소개와 시작하기를 확인할 수 있어요."],
        "홈으로",
        "홈으로 안내해 드릴게요.",
    ),
]

# 생성 의도 시 여러 선택지(자동화/썸네일/비디오)를 주기 위한 다중 액션 카드
# (키워드 목록, 카드 제목, bullets, [(버튼 라벨, 경로), ...], 즉시 응답용 메시지)
INTENT_CHOICES: list[
    tuple[list[str], str, list[str], list[tuple[str, str]], str]
] = [
    (
        ["생성", "생성하러", "생성하러 가", "만들러", "만들러 가", "만들기", "콘텐츠 생성"],
        "어디로 가시겠어요?",
        [
            "자동화 파이프라인으로 콘텐츠 생성",
            "썸네일만 만들기",
            "비디오만 만들기",
        ],
        [
            ("자동화하러 가기", "/pipeline/create"),
            ("썸네일만 생성", "/pipeline/thumbnail"),
            ("비디오만 생성", "/pipeline/video"),
        ],
        "어디로 가실지 아래에서 골라 주세요.",
    ),
]


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

        # 인사·간단 패턴이면 LLM/RAG 없이 즉시 응답 (응답 속도 개선)
        if self._is_greeting_or_simple(text):
            session.add_message("user", text)
            answer = self._get_greeting_reply()
            session.add_message("ai", answer)
            return {
                "session_id": session.session_id,
                "message": answer,
                "card": None,
                "sources": [],
            }

        # 의도(요금제/로그인/파이프라인/생성 선택지 등)가 잡히면 LLM 없이 고정 메시지+카드 즉시 반환
        intent_card = self._detect_intent_link(text)
        if intent_card:
            reply_message = intent_card.get("message", "해당 페이지로 안내해 드릴게요.")
            session.add_message("user", text)
            session.add_message("ai", reply_message)
            card = self._sanitize_card(intent_card)
            return {
                "session_id": session.session_id,
                "message": reply_message,
                "card": card,
                "sources": [],
            }

        # 1. 쿼리 최적화 (인사/단문이면 LLM 호출 생략)
        session.add_message("user", text)
        if self._should_skip_query_lookup(text):
            search_query = ""
        else:
            search_query = await self._generate_search_query(session, text)

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
        # 의도 기반 링크 안내: 카드가 없거나 링크가 없을 때 감지된 의도로 카드 보강
        intent_card = self._detect_intent_link(text)
        if intent_card and (
            card is None or (not card.get("action") and not card.get("url"))
        ):
            card = self._sanitize_card(intent_card)

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

    def _normalize_for_pattern(self, text: str) -> str:
        """패턴 매칭용: 공백 제거, 소문자."""
        return re.sub(r"\s+", "", text).lower().strip()

    def _is_greeting_or_simple(self, text: str) -> bool:
        """인사·간단 문구면 True (즉시 응답 대상)."""
        normalized = self._normalize_for_pattern(text)
        if not normalized or len(normalized) > 30:
            return False
        return any(p.lower() in normalized for p in GREETING_PATTERNS)

    def _get_greeting_reply(self) -> str:
        """인사 시 반환할 고정 답변."""
        return GREETING_REPLY

    def _should_skip_query_lookup(self, text: str) -> bool:
        """인사/단문이면 쿼리 LLM 호출 생략 (단계 2). 짧은 문장은 검색 불필요로 간주."""
        stripped = text.strip()
        return len(stripped) <= 8

    def _detect_intent_link(self, message: str) -> dict[str, Any] | None:
        """사용자 메시지에서 의도(요금제/로그인/파이프라인 등)를 감지해 해당 링크 카드를 반환.
        '생성' 의도는 다중 선택지(자동화/썸네일/비디오) 카드로 반환."""
        normalized = self._normalize_for_pattern(message)
        if not normalized:
            return None
        # 생성 의도: 여러 선택지 카드 (actions 배열)
        for keywords, title, bullets, choices, intent_message in INTENT_CHOICES:
            if any(kw.lower() in normalized or kw in message for kw in keywords):
                return {
                    "title": title,
                    "bullets": bullets,
                    "actions": [{"label": label, "action": path} for label, path in choices],
                    "message": intent_message,
                }
        for keywords, path, title, bullets, cta, intent_message in INTENT_LINKS:
            if any(kw.lower() in normalized or kw in message for kw in keywords):
                return {
                    "title": title,
                    "bullets": bullets,
                    "cta": cta,
                    "action": path,
                    "message": intent_message,
                }
        return None

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
        action = card.get("action")
        url = card.get("url")
        actions = card.get("actions")

        if not isinstance(title, str) or not title.strip():
            return None
        if not isinstance(bullets, list):
            return None

        cleaned_bullets = [str(b).strip() for b in bullets if str(b).strip()]
        if not cleaned_bullets:
            return None

        cleaned: dict[str, Any] = {
            "title": title.strip(),
            "bullets": cleaned_bullets,
        }
        if isinstance(cta, str) and cta.strip():
            cleaned["cta"] = cta.strip()
        if isinstance(action, str) and action.strip():
            cleaned["action"] = action.strip()
        if isinstance(url, str) and url.strip():
            cleaned["url"] = url.strip()
        # 다중 선택지 카드(생성 → 자동화/썸네일/비디오)
        if isinstance(actions, list) and actions:
            cleaned_actions = []
            for item in actions:
                if not isinstance(item, dict):
                    continue
                lbl = item.get("label")
                act = item.get("action")
                u = item.get("url")
                if isinstance(lbl, str) and lbl.strip():
                    entry: dict[str, Any] = {"label": lbl.strip()}
                    if isinstance(act, str) and act.strip():
                        entry["action"] = act.strip()
                    if isinstance(u, str) and u.strip():
                        entry["url"] = u.strip()
                    if "action" in entry or "url" in entry:
                        cleaned_actions.append(entry)
            if cleaned_actions:
                cleaned["actions"] = cleaned_actions
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

        # 인사·간단 패턴이면 LLM/RAG 없이 즉시 응답 (응답 속도 개선)
        if self._is_greeting_or_simple(text):
            session.add_message("user", text)
            answer = self._get_greeting_reply()
            session.add_message("ai", answer)
            yield f"data: {json.dumps({'step': 'done', 'full_text': answer, 'card': None, 'session_id': session.session_id}, ensure_ascii=False)}\n\n"
            return

        # 의도(요금제/로그인/파이프라인/생성 선택지 등)가 잡히면 스트리밍 없이 고정 메시지+카드 즉시 반환
        intent_card = self._detect_intent_link(text)
        if intent_card:
            reply_message = intent_card.get("message", "해당 페이지로 안내해 드릴게요.")
            session.add_message("user", text)
            session.add_message("ai", reply_message)
            card = self._sanitize_card(intent_card)
            yield f"data: {json.dumps({'step': 'done', 'full_text': reply_message, 'card': card, 'session_id': session.session_id}, ensure_ascii=False)}\n\n"
            return

        # 1. 쿼리 최적화 (인사/단문이면 LLM 호출 생략)
        session.add_message("user", text)
        if self._should_skip_query_lookup(text):
            search_query = ""
        else:
            yield f"data: {json.dumps({'step': 'searching', 'message': '질문을 분석하고 있습니다...'}, ensure_ascii=False)}\n\n"
            search_query = await self._generate_search_query(session, text)

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
            # 의도 기반 링크 안내 (일반 응답과 동일)
            intent_card = self._detect_intent_link(text)
            if intent_card and (
                card is None or (not card.get("action") and not card.get("url"))
            ):
                card = self._sanitize_card(intent_card)

            session.add_message("ai", answer)

            yield f"data: {json.dumps({'step': 'done', 'full_text': answer, 'card': card, 'session_id': session.session_id}, ensure_ascii=False)}\n\n"

        except Exception as e:
            log_llm_fail("챗봇 스트리밍", str(e))
            log_error(f"챗봇 스트리밍 실패: {e}")
            yield f"data: {json.dumps({'error': '죄송합니다. 응답 생성 중 오류가 발생했습니다.'}, ensure_ascii=False)}\n\n"
