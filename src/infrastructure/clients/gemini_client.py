"""
Gemini AI 클라이언트
Vertex AI 기반 텍스트/이미지 생성
"""

import asyncio
import json
import re
import time
from collections.abc import Callable
from typing import Any

from config.constants import HOOK_TEMPLATES, HOOK_TYPES
from core.exceptions import GeminiAPIError
from core.prompts import (
    prompt_registry,
)
from utils.cache import cached
from utils.logger import get_logger, log_llm_fail, log_llm_request, log_llm_response
from utils.retry import retry_on_error

logger = get_logger(__name__)


class GeminiClient:
    """Gemini AI 클라이언트"""

    def __init__(
        self,
        project_id: str,
        location: str,
        text_model: str = "gemini-3-pro-preview",
        image_model: str = "gemini-3-pro-image-preview",
        embedding_model: str = "text-embedding-004",
    ) -> None:
        self._project_id = project_id
        self._location = location
        self._text_model = text_model
        self._image_model = image_model
        self._embedding_model = embedding_model
        self._client = None
        self._async_client = None
        self._async_client_loop = None

    def _get_client(self):
        """Gemini 클라이언트 인스턴스 반환 (지연 초기화)"""
        if self._client is None:
            from google import genai

            self._client = genai.Client(
                vertexai=True,
                project=self._project_id,
                location=self._location,
            )
        return self._client

    def is_configured(self) -> bool:
        """설정 확인"""
        return bool(self._project_id and self._location)

    def health_check(self) -> bool:
        """API 연결 상태 확인"""
        try:
            self._get_client()
            return True
        except Exception:
            return False

    def _get_async_client(self):
        """비동기 Gemini 클라이언트 인스턴스 반환"""
        from google import genai

        return genai.Client(
            vertexai=True,
            project=self._project_id,
            location=self._location,
        )

    async def generate_content_async(
        self,
        prompt: str,
        temperature: float = 0.7,
        use_grounding: bool = False,
        max_retries: int = 3,
        model: str | None = None,
    ) -> str:
        """비동기 텍스트 생성 (sync 호출을 thread로 감싸기)"""
        last_error = None
        for attempt in range(max_retries):
            try:
                return await asyncio.to_thread(
                    self.generate_text,
                    prompt,
                    temperature=temperature,
                    use_grounding=use_grounding,
                    model=model,
                )
            except Exception as e:
                last_error = e
                # ... (error handling logic same as before) ...
                error_str = str(e).lower()
                is_rate_limit = any(
                    keyword in error_str for keyword in ["429", "rate limit", "quota"]
                )
                if is_rate_limit and attempt < max_retries - 1:
                    delay = min(1.0 * (2**attempt), 10.0)
                    logger.warning(
                        f"Rate limit, {delay}초 후 재시도 ({attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(delay)
                else:
                    break

        log_llm_fail("텍스트 생성(비동기)", str(last_error))
        return ""

    async def generate_content_stream(
        self,
        prompt: str,
        temperature: float = 0.7,
        use_grounding: bool = False,
        model: str | None = None,
    ):
        """비동기 텍스트 생성 (스트리밍)"""
        from google.genai import types

        client = self._get_client()
        config = types.GenerateContentConfig(temperature=temperature)
        target_model = model or self._text_model

        if use_grounding:
            config.tools = [types.Tool(google_search=types.GoogleSearch())]

        def _get_stream():
            return client.models.generate_content_stream(
                model=target_model,
                contents=prompt,
                config=config,
            )

        stream = await asyncio.to_thread(_get_stream)

        try:
            for chunk in stream:
                yield chunk.text
                await asyncio.sleep(0)
        except Exception:
            pass

    async def generate_text_async(
        self,
        prompt: str,
        temperature: float = 0.7,
        use_grounding: bool = False,
        max_retries: int = 3,
        model: str | None = None,
    ) -> str:
        """generate_content_async 별칭 (호환성 유지)"""
        return await self.generate_content_async(
            prompt,
            temperature=temperature,
            use_grounding=use_grounding,
            max_retries=max_retries,
            model=model,
        )

    def _extract_embedding_values(self, response: Any) -> list[float]:
        """embed_content 응답에서 embedding 벡터(list[float])를 최대한 보수적으로 추출한다."""
        if response is None:
            raise GeminiAPIError("임베딩 응답이 비어 있습니다.")

        # 1) google-genai 스타일: response.embeddings[0].values
        embeddings = getattr(response, "embeddings", None)
        if embeddings:
            first = embeddings[0]
            values = getattr(first, "values", None)
            if values is not None:
                return list(values)
            embedding_obj = getattr(first, "embedding", None)
            values = getattr(embedding_obj, "values", None)
            if values is not None:
                return list(values)

        # 2) 단일 응답: response.embedding.values
        embedding_obj = getattr(response, "embedding", None)
        values = getattr(embedding_obj, "values", None)
        if values is not None:
            return list(values)

        # 3) dict 스타일(방어)
        if isinstance(response, dict):
            emb_list = response.get("embeddings")
            if isinstance(emb_list, list) and emb_list:
                first = emb_list[0]
                if isinstance(first, dict):
                    values = first.get("values")
                    if isinstance(values, list):
                        return [float(x) for x in values]
                    embedding_obj = first.get("embedding")
                    if isinstance(embedding_obj, dict):
                        values = embedding_obj.get("values")
                        if isinstance(values, list):
                            return [float(x) for x in values]
            embedding_obj = response.get("embedding")
            if isinstance(embedding_obj, dict):
                values = embedding_obj.get("values")
                if isinstance(values, list):
                    return [float(x) for x in values]

        raise GeminiAPIError("임베딩 응답 형식을 파싱할 수 없습니다.")

    def get_embedding_sync(self, text: str, *, model: str | None = None) -> list[float]:
        """텍스트 임베딩 생성(동기).

        파이프라인(예: TwoTowerSource)에서 사용한다.
        """
        import time as _time

        text = (text or "").strip()
        if not text:
            return []

        model_name = model or self._embedding_model
        start_time = _time.time()

        log_llm_request(
            "임베딩 생성",
            details=f"model={model_name}",
            model=model_name,
            prompt_preview=text[:400],
        )

        try:
            client = self._get_client()

            def _api_call():
                # google-genai: embed_content
                return client.models.embed_content(
                    model=model_name,
                    contents=text,
                )

            response = self.retry_with_backoff(_api_call)
            values = self._extract_embedding_values(response)
            elapsed_ms = (_time.time() - start_time) * 1000

            log_llm_response(
                "임베딩 생성",
                details=f"{len(values)} dims",
                duration_ms=elapsed_ms,
            )
            return values

        except Exception as e:
            # 호출부에서 zeros fallback을 하므로, 여기서는 의미있는 에러만 남긴다.
            log_llm_fail("임베딩 생성", str(e), model=model_name)
            raise GeminiAPIError(f"임베딩 생성 실패: {e}") from e

    async def get_embedding(self, text: str, *, model: str | None = None) -> list[float]:
        """텍스트 임베딩 생성(비동기).

        내부적으로 동기 API를 thread로 감싸되, thread 실행이 실패하면 동기 호출로 fallback한다.
        """
        try:
            return await asyncio.to_thread(self.get_embedding_sync, text, model=model)
        except Exception:
            # Cloud Run 환경에서 to_thread가 실패하는 경우는 드물지만, 안전한 fallback 제공.
            return self.get_embedding_sync(text, model=model)

    @cached(ttl=3600, cache_key_prefix="gemini")
    @retry_on_error(max_attempts=3, base_delay=1.0, max_delay=8.0)
    def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        use_grounding: bool = False,
        model: str | None = None,
    ) -> str:
        """텍스트 생성 (재시도 로직 적용)"""
        import time as _time

        start_time = _time.time()
        target_model = model or self._text_model

        log_llm_request(
            "텍스트 생성",
            details=f"temperature={temperature}, grounding={use_grounding}",
            model=target_model,
            prompt_preview=prompt,
        )
        try:
            from google.genai import types

            client = self._get_client()

            config = types.GenerateContentConfig(temperature=temperature)

            if use_grounding:
                config.tools = [types.Tool(google_search=types.GoogleSearch())]

            # [AI Product Pattern] Retry Mechanism
            def _api_call():
                return client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=config,
                )

            response = self.retry_with_backoff(_api_call)
            elapsed_ms = (_time.time() - start_time) * 1000

            response_text = response.text if response and response.text else ""
            log_llm_response(
                "텍스트 생성",
                details=f"응답 {len(response_text)}자",
                response_preview=response_text,
                duration_ms=elapsed_ms,
            )
            return response_text

        except Exception as e:
            log_llm_fail("텍스트 생성", str(e), model=self._text_model)
            raise GeminiAPIError(f"텍스트 생성 실패: {e}") from e

    @retry_on_error(max_attempts=3, base_delay=1.0, max_delay=8.0)
    def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
    ) -> bytes | None:
        """이미지 생성 (Retry 적용) (genesis_kr/v3 방식: generate_content + response_modalities)"""
        import time as _time

        start_time = _time.time()

        log_llm_request(
            "이미지 생성",
            details=f"aspect_ratio={aspect_ratio}",
            model=self._image_model,
            prompt_preview=prompt,
        )
        try:
            import base64

            from google.genai.types import GenerateContentConfig, Modality

            client = self._get_client()

            # [AI Product Pattern] Retry Mechanism
            def _api_call():
                return client.models.generate_content(
                    model=self._image_model,
                    contents=prompt,
                    config=GenerateContentConfig(
                        response_modalities=[Modality.TEXT, Modality.IMAGE],
                    ),
                )

            response = self.retry_with_backoff(_api_call)
            elapsed_ms = (_time.time() - start_time) * 1000

            # 이미지가 포함된 응답 처리
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        img_data = part.inline_data.data
                        if isinstance(img_data, str):
                            img_data = base64.b64decode(img_data)
                        log_llm_response(
                            "이미지 생성",
                            details=f"{len(img_data):,} bytes 이미지 생성됨",
                            duration_ms=elapsed_ms,
                        )
                        return img_data

            log_llm_fail("이미지 생성", "응답에 이미지 없음", model=self._image_model)
            return None

        except Exception as e:
            log_llm_fail("이미지 생성", str(e), model=self._image_model)
            raise GeminiAPIError(f"이미지 생성 실패: {e}") from e

    @cached(ttl=7200, cache_key_prefix="gemini")
    @retry_on_error(max_attempts=3, base_delay=1.0, max_delay=8.0)
    def analyze_marketing_data(
        self,
        youtube_data: dict,
        naver_data: dict,
        product_name: str,
        top_insights: list[dict] | None = None,
        market_trends: dict | None = None,
        progress_callback: Callable[[str, int], None] | None = None,
        use_search_grounding: bool = True,
    ) -> dict[str, Any]:
        """마케팅 데이터 분석 (Retry & Validation 강화)"""
        import time as _time

        start_time = _time.time()

        try:
            from google.genai import types

            client = self._get_client()

            if progress_callback:
                progress_callback("마케팅 데이터 분석 중...", 20)

            analysis_prompt = prompt_registry.get("marketing.analysis").render(
                product_name=product_name,
                top_insights_json=(
                    json.dumps(top_insights, ensure_ascii=False, indent=2)
                    if top_insights
                    else "데이터 없음"
                ),
                market_trends_json=(
                    json.dumps(market_trends, ensure_ascii=False, indent=2)
                    if market_trends
                    else "데이터 없음"
                ),
                youtube_data_json=(
                    json.dumps(youtube_data, ensure_ascii=False, indent=2)
                    if youtube_data
                    else "데이터 없음"
                ),
                naver_data_json=(
                    json.dumps(naver_data, ensure_ascii=False, indent=2)
                    if naver_data
                    else "데이터 없음"
                ),
            )

            log_llm_request(
                "마케팅 분석",
                details=f"제품: {product_name}, grounding={use_search_grounding}",
                model=self._text_model,
                prompt_preview=analysis_prompt,
            )

            if progress_callback:
                progress_callback("AI 분석 진행 중...", 50)

            config = types.GenerateContentConfig(
                temperature=0.7,
                response_mime_type="application/json",
            )

            if use_search_grounding:
                config.tools = [types.Tool(google_search=types.GoogleSearch())]

            # [AI Product Pattern] Retry Mechanism
            def _api_call():
                return client.models.generate_content(
                    model=self._text_model,
                    contents=analysis_prompt,
                    config=config,
                )

            response = self.retry_with_backoff(_api_call)
            elapsed_ms = (_time.time() - start_time) * 1000

            if progress_callback:
                progress_callback("분석 결과 처리 중...", 80)

            result = self._validate_json_output(response.text)
            response_text = response.text if response and response.text else ""

            log_llm_response(
                "마케팅 분석",
                details=f"JSON {len(response_text)}자 수신",
                response_preview=response_text,
                duration_ms=elapsed_ms,
            )

            if progress_callback:
                progress_callback("분석 완료!", 100)

            return result

        except Exception as e:
            log_llm_fail("마케팅 분석", str(e), model=self._text_model)
            if progress_callback:
                progress_callback(f"오류: {e}", 0)
            return {"error": str(e)}

    def generate_marketing_strategy(
        self,
        collected_data: dict,
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> dict[str, Any]:
        """마케팅 전략 생성"""
        product = collected_data.get("product", {})
        product_name = product.get("name", "제품")

        youtube_data = collected_data.get("youtube_data", {})
        naver_data = collected_data.get("naver_data", {})
        top_insights = collected_data.get("top_insights", [])
        market_trends = collected_data.get("market_trends")

        return self.analyze_marketing_data(
            youtube_data=youtube_data,
            naver_data=naver_data,
            product_name=product_name,
            top_insights=top_insights,
            market_trends=market_trends,
            progress_callback=progress_callback,
            use_search_grounding=True,
        )

    def _build_image_prompt(
        self,
        product: dict,
        hook_text: str,
        style: str = "드라마틱",
        color_scheme: str = "블루 그라디언트",
        layout: str = "중앙 집중형",
        style_modifier: str | None = None,
        aspect_ratio: str = "16:9",
    ) -> str:
        """마케팅 이미지 생성 프롬프트 빌드"""
        product_name = product.get("name", "제품")
        product_category = product.get("category", "일반")

        prompt = f"""### 🤖 Role: Premium E-commerce Visual Designer
You are an expert commercial photographer and digital artist specializing in high-conversion e-commerce imagery.
Your mission: Create a thumbnail that stops the scroll and drives immediate purchase intent.

### 🎯 Product Context
- **Product Name:** {product_name}
- **Category:** {product_category}
- **Hook Text:** "{hook_text}"

### 🎨 Visual Direction
- **Style:** {style} with high-end commercial quality
- **Color Scheme:** {color_scheme}
- **Layout:** {layout}
"""
        if style_modifier:
            prompt += f"- **Style Modifier:** {style_modifier}\n"

        prompt += f"""
### 📐 Composition Requirements
- **Hero Element:** Product must be the undeniable focal point
- **Background:** Clean, uncluttered, complementary to product colors
- **Lighting:** Dramatic studio lighting with soft, professional shadows
- **Depth:** Subtle depth-of-field to separate product from background
- **Safe Zone:** Leave 10% margin on all edges for platform UI overlay

### ✍️ Text Overlay (CRITICAL)
- **Text Content:** "{hook_text}"
- **Placement:** Prominent, readable at thumbnail size
- **Typography:** Modern, bold sans-serif (no script or thin fonts)
- **Contrast:** High contrast against background (use text shadow or backing)
- **Size:** Large enough to read on mobile (at least 15% of image height)

### 🔧 Technical Specifications
- **Resolution:** 8K quality, ultra-sharp details
- **Aspect Ratio:** {aspect_ratio}
- **Render Style:** Photorealistic with subtle enhancement
- **Color Profile:** Vibrant but natural, Instagram-ready

### 💎 Mood & Emotion
- **Premium Feel:** Luxurious, trustworthy, professional craftsmanship
- **Urgency:** Visual cues that create FOMO (limited, exclusive vibe)
- **Desire:** Make viewers imagine owning this product
- **Action:** Subtle visual flow guiding eye to key elements

### ⛔ Negative Constraints (AVOID)
- NO watermarks, logos, or brand identifiers (unless requested)
- NO cluttered or busy backgrounds
- NO unrealistic or distorted product proportions
- NO low-quality textures or blurry elements
- NO generic stock photo aesthetics
"""
        return prompt.strip()

    def generate_thumbnail(
        self,
        product: dict,
        hook_text: str,
        style: str = "드라마틱",
        style_modifier: str | None = None,
        aspect_ratio: str = "16:9",
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> bytes | None:
        """마케팅 썸네일 생성"""
        import time as _time

        start_time = _time.time()
        p_name = product.get("name", "N/A")

        try:
            if progress_callback:
                progress_callback("프롬프트 구성 중...", 10)

            prompt = self._build_image_prompt(
                product,
                hook_text,
                style,
                style_modifier=style_modifier,
                aspect_ratio=aspect_ratio,
            )

            log_llm_request(
                "썸네일 생성",
                details=f"제품: {p_name}, 스타일: {style}, 비율: {aspect_ratio}",
                model=self._image_model,
                prompt_preview=prompt,
            )

            if progress_callback:
                progress_callback("이미지 생성 중...", 30)

            image_data = self.generate_image(prompt, aspect_ratio=aspect_ratio)

            if progress_callback:
                progress_callback("이미지 처리 중...", 80)

            elapsed_ms = (_time.time() - start_time) * 1000

            if image_data:
                log_llm_response(
                    "썸네일 생성",
                    details=f"{len(image_data):,} bytes 썸네일 생성 완료",
                    duration_ms=elapsed_ms,
                )
                if progress_callback:
                    progress_callback("썸네일 준비 완료!", 100)
                return image_data

            return None

        except Exception as e:
            log_llm_fail("썸네일 생성", str(e), model=self._image_model)
            if progress_callback:
                progress_callback(f"오류: {e}", 0)
            return None

    def generate_multiple_thumbnails(
        self,
        product: dict,
        hook_texts: list[str],
        styles: list[str] | None = None,
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> list[dict]:
        """다중 썸네일 생성"""
        p_name = product.get("name", "N/A")
        log_llm_request("다중 썸네일 생성", f"제품: {p_name}, {len(hook_texts)}개")

        if styles is None:
            styles = ["네오브루탈리즘", "비비드", "누아르"]

        results = []
        total = len(hook_texts)

        for i, hook_text in enumerate(hook_texts):
            style = styles[i % len(styles)]

            if progress_callback:
                progress = int((i / total) * 100)
                progress_callback(f"썸네일 {i + 1}/{total} 생성 중...", progress)

            image = self.generate_thumbnail(product, hook_text, style)

            if image:
                results.append(
                    {
                        "image": image,
                        "hook_text": hook_text,
                        "style": style,
                    }
                )

        log_llm_response("다중 썸네일 생성", f"{len(results)}/{total}개 완료")

        if progress_callback:
            progress_callback("모든 썸네일 생성 완료!", 100)

        return results

    def generate_hook_texts(
        self,
        product_name: str,
        hook_types: list[str] | None = None,
        count: int = 5,
        custom_params: dict | None = None,
    ) -> list[dict]:
        """심리학 기반 훅 텍스트 생성"""
        if hook_types is None:
            hook_types = HOOK_TYPES

        params = {
            "product": product_name,
            "count": "10만",
            "discount": "50",
            "benefit": "효과",
            **(custom_params or {}),
        }

        hooks = []
        for hook_type in hook_types:
            if hook_type in HOOK_TEMPLATES:
                for template in HOOK_TEMPLATES[hook_type]:
                    try:
                        hook = template.format(**params)
                        hooks.append({"text": hook, "type": hook_type})
                    except KeyError:
                        continue

        # 중복 제거 및 개수 제한
        seen = set()
        unique_hooks = []
        for h in hooks:
            if h["text"] not in seen:
                seen.add(h["text"])
                unique_hooks.append(h)
                if len(unique_hooks) >= count:
                    break

        return unique_hooks

    def _extract_first_json_object(self, text: str) -> str | None:
        """첫 번째 완전한 { ... } 블록만 추출 (중첩 괄호 대응)."""
        start = text.find("{")
        if start == -1:
            return None
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
        return None

    def _fix_common_json_issues(self, raw: str) -> str:
        """LLM이 자주 내는 JSON 오류 보정 (끝 쉼표 등)."""
        raw = re.sub(r",\s*}", "}", raw)
        raw = re.sub(r",\s*]", "]", raw)
        return raw

    def _validate_json_output(
        self,
        text: str,
        required_fields: list[str] | None = None,
    ) -> dict:
        """LLM 출력 JSON 검증 및 정화"""
        # [AI Product Pattern] Output Sanitization
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        text = text.strip()

        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            json_str = self._extract_first_json_object(text)
            if json_str:
                fixed = self._fix_common_json_issues(json_str)
                try:
                    result = json.loads(fixed)
                except json.JSONDecodeError:
                    return {"error": "JSON 파싱 실패", "raw_text": text[:500]}
            else:
                return {"error": "JSON을 찾을 수 없음", "raw_text": text[:500]}

        if required_fields:
            missing = [f for f in required_fields if f not in result]
            if missing:
                result["_validation_warning"] = f"누락된 필드: {missing}"

        return result

    def retry_with_backoff(
        self,
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
    ):
        """지수 백오프 재시도"""
        last_error = None

        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = min(base_delay * (2**attempt), max_delay)
                    logger.info(
                        f"재시도 {attempt + 1}/{max_retries} ({delay:.1f}초 후)"
                    )
                    time.sleep(delay)

        raise last_error  # type: ignore
