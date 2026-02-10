from __future__ import annotations

import json
import logging
from typing import Any

from core.prompts import prompt_registry
from core.prompts.veo_prompt_engine import VeoPromptEngine
from infrastructure.clients.gemini_client import GeminiClient
from utils.logger import log_feature_end, log_feature_fail, log_feature_start

logger = logging.getLogger(__name__)


class StudioService:
    """
    Studio 전용 서비스: 프롬프트 직접 편집 및 고도화 지원
    (자동화 파이프라인 외부에서 독립적으로 동작)
    """

    def __init__(self, gemini_client: GeminiClient):
        self._gemini = gemini_client

    async def generate_draft_prompts(
        self,
        product_name: str,
        product_desc: str,
        hook_text: str,
        style: str = "Cinematic",
        camera_movement: str | None = None,
        composition: str | None = None,
        lighting_mood: str | None = None,
        brand_kit: dict | None = None,
    ) -> dict[str, Any]:
        """
        초합 프롬프트 생성 (비디오 및 썸네일 통합)
        """
        # 초안 생성 시작 로깅
        log_feature_start("studio_generate_draft", product_name)
        prompt_text = VeoPromptEngine.construct_generation_prompt(
            product_name=product_name,
            product_desc=product_desc,
            hook_text=hook_text,
            style=style,
            camera_movement=camera_movement,
            composition=composition,
            lighting_mood=lighting_mood,
            brand_kit=brand_kit,
        )

        try:
            response = await self._gemini.generate_text_async(prompt_text)
            # JSON 클렌징 및 로딩
            import re

            cleaned = re.sub(r"^```(?:json)?\s*", "", response.strip())
            cleaned = re.sub(r"\s*```\s*$", "", cleaned)
            res = json.loads(cleaned)
            log_feature_end("studio_generate_draft")
            return res
        except Exception as e:
            log_feature_fail("studio_generate_draft", str(e))
            logger.error(f"Studio draft generation failed: {e}")
            return {
                "veo_prompt": "Error generating draft.",
                "negative_prompt": "text, watermark",
                "metadata": {},
            }

    async def refine_prompt(
        self,
        original_prompt: str,
        user_feedback: str,
        brand_kit: dict | None = None,
    ) -> dict[str, Any]:
        """
        사용자 피드백을 반영한 프롬프트 고도화 (Refinement)
        """
        log_feature_start("studio_refine_prompt")
        template = prompt_registry.get_template("studio.refine")

        brand_summary = "N/A"
        if brand_kit:
            brand_summary = f"{brand_kit.get('name')} (Color: {brand_kit.get('primary_color')}, Mood: {brand_kit.get('tone_and_voice')})"

        prompt_text = template.format(
            original_prompt=original_prompt,
            user_feedback=user_feedback,
            brand_kit_summary=brand_summary,
        )

        try:
            response = await self._gemini.generate_text_async(prompt_text)
            import re

            cleaned = re.sub(r"^```(?:json)?\s*", "", response.strip())
            cleaned = re.sub(r"\s*```\s*$", "", cleaned)
            res = json.loads(cleaned)
            log_feature_end("studio_refine_prompt")
            return res
        except Exception as e:
            log_feature_fail("studio_refine_prompt", str(e))
            logger.error(f"Studio prompt refinement failed: {e}")
            return {
                "refined_prompt": original_prompt,
                "changes_made": "Error occurred.",
                "director_notes": "프롬프트 고도화 중 오류가 발생했습니다.",
            }
