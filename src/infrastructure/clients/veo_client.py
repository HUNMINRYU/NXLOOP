"""
Veo 비디오 생성 클라이언트
Vertex AI Veo 3.1 기반 마케팅 비디오 생성
"""

import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from config.constants import CAMERA_MOTIONS
from core.exceptions import VeoAPIError
from utils.logger import (
    get_logger,
    log_api_end,
    log_api_start,
    log_error,
    log_llm_fail,
    log_llm_request,
    log_llm_response,
    log_process,
    log_timing,
)

logger = get_logger(__name__)


# === Camera Movement Presets (Veo 3.1 프롬프트 가이드 기반) ===
CAMERA_MOVEMENTS = {
    "dolly_in": {
        "name": "Dolly In",
        "name_ko": "전진 달리",
        "prompt": "slow dolly push-in towards the subject",
        "description": "피사체를 향해 부드럽게 전진",
    },
    "dolly_out": {
        "name": "Dolly Out",
        "name_ko": "후진 달리",
        "prompt": "smooth dolly pull-out revealing the scene",
        "description": "장면을 드러내며 후진",
    },
    "orbit": {
        "name": "Orbit",
        "name_ko": "360도 회전",
        "prompt": "slow 360° orbit around the subject (thats where the camera is)",
        "description": "피사체 주위를 원형으로 회전",
    },
    "crane_up": {
        "name": "Crane Up",
        "name_ko": "크레인 상승",
        "prompt": "cinematic crane shot rising from low to reveal the scene",
        "description": "낮은 위치에서 상승하며 장면 공개",
    },
    "crane_down": {
        "name": "Crane Down",
        "name_ko": "크레인 하강",
        "prompt": "elegant crane descent from high angle to eye level",
        "description": "높은 각도에서 눈높이로 하강",
    },
    "tracking": {
        "name": "Tracking",
        "name_ko": "트래킹",
        "prompt": "smooth side-to-side tracking shot following the action",
        "description": "액션을 따라가는 횡이동",
    },
    "steadicam": {
        "name": "Steadicam",
        "name_ko": "스테디캠",
        "prompt": "fluid steadicam movement with natural float",
        "description": "흔들림 없는 부드러운 이동",
    },
    "handheld": {
        "name": "Handheld",
        "name_ko": "핸드헬드",
        "prompt": "slightly shaky handheld shot for documentary feel",
        "description": "다큐멘터리 느낌의 손떨림",
    },
    "static": {
        "name": "Static",
        "name_ko": "고정",
        "prompt": "locked-off static shot with subtle parallax",
        "description": "고정된 카메라 앵글",
    },
    "pov": {
        "name": "POV",
        "name_ko": "1인칭 시점",
        "prompt": "first-person POV shot from subject's perspective",
        "description": "피사체 시점의 1인칭",
    },
    "aerial": {
        "name": "Aerial/Drone",
        "name_ko": "항공/드론",
        "prompt": "smooth aerial drone shot descending into the scene",
        "description": "드론 촬영 느낌의 항공 뷰",
    },
}

# === Composition Presets ===
COMPOSITIONS = {
    "wide": {
        "name": "Wide Shot",
        "name_ko": "와이드 샷",
        "prompt": "wide establishing shot",
    },
    "medium": {"name": "Medium Shot", "name_ko": "미디엄 샷", "prompt": "medium shot"},
    "close_up": {"name": "Close-up", "name_ko": "클로즈업", "prompt": "close-up shot"},
    "extreme_close_up": {
        "name": "Extreme Close-up",
        "name_ko": "익스트림 클로즈업",
        "prompt": "extreme close-up macro shot",
    },
    "over_shoulder": {
        "name": "Over Shoulder",
        "name_ko": "오버 숄더",
        "prompt": "over-the-shoulder shot",
    },
    "low_angle": {
        "name": "Low Angle",
        "name_ko": "로우 앵글",
        "prompt": "dramatic low-angle shot looking up",
    },
    "high_angle": {
        "name": "High Angle",
        "name_ko": "하이 앵글",
        "prompt": "top-down high-angle shot",
    },
    "dutch_angle": {
        "name": "Dutch Angle",
        "name_ko": "더치 앵글",
        "prompt": "tilted dutch angle for tension",
    },
}

# === Lighting/Mood Presets ===
LIGHTING_MOODS = {
    "golden_hour": {
        "name": "Golden Hour",
        "name_ko": "골든아워",
        "prompt": "warm golden hour lighting with long shadows",
    },
    "blue_hour": {
        "name": "Blue Hour",
        "name_ko": "블루아워",
        "prompt": "cool blue hour twilight atmosphere",
    },
    "studio": {
        "name": "Studio",
        "name_ko": "스튜디오",
        "prompt": "professional studio lighting with key, fill and rim lights",
    },
    "dramatic": {
        "name": "Dramatic",
        "name_ko": "드라마틱",
        "prompt": "high contrast dramatic chiaroscuro lighting",
    },
    "soft": {
        "name": "Soft",
        "name_ko": "소프트",
        "prompt": "soft diffused natural lighting",
    },
    "neon": {
        "name": "Neon",
        "name_ko": "네온",
        "prompt": "vibrant neon lighting with colorful reflections",
    },
    "moody": {
        "name": "Moody",
        "name_ko": "무드",
        "prompt": "moody atmospheric lighting with haze",
    },
    "natural": {
        "name": "Natural",
        "name_ko": "자연광",
        "prompt": "natural daylight from window",
    },
}

# === Audio Presets ===
AUDIO_PRESETS = {
    "cinematic": {
        "name": "Cinematic",
        "name_ko": "시네마틱",
        "prompt": "cinematic orchestral score with emotional swell",
    },
    "upbeat": {
        "name": "Upbeat",
        "name_ko": "업비트",
        "prompt": "upbeat modern electronic pop music",
    },
    "ambient": {
        "name": "Ambient",
        "name_ko": "앰비언트",
        "prompt": "subtle ambient drone with atmospheric sounds",
    },
    "dramatic": {
        "name": "Dramatic",
        "name_ko": "드라마틱",
        "prompt": "tense dramatic score building to climax",
    },
    "calm": {
        "name": "Calm",
        "name_ko": "차분한",
        "prompt": "soft piano with gentle nature sounds",
    },
    "corporate": {
        "name": "Corporate",
        "name_ko": "기업용",
        "prompt": "professional corporate background music",
    },
    "asmr": {
        "name": "ASMR",
        "name_ko": "ASMR",
        "prompt": "hyper-realistic ASMR foley, crisp tactile textures, high-fidelity proximity sounds",
    },
    "silent": {
        "name": "Silent",
        "name_ko": "무음",
        "prompt": "absolute minimalism, focus on microscopic atmospheric air sounds, no music",
    },
}


@dataclass
class AdvancedPromptBuilder:
    """
    Veo 3.1 고급 프롬프트 빌더
    Google AI 프롬프트 가이드 기반 7가지 요소 조합
    """

    # 필수 요소
    subject: str = ""
    action: str = ""

    # 선택 요소
    environment: str = ""
    style: str = ""
    camera_movement: str = "static"
    composition: str = "medium"
    lighting_mood: str = "natural"

    # 오디오 요소
    audio_preset: str = "cinematic"
    dialogue: str = ""
    sfx: list[str] = field(default_factory=list)
    ambient: str = ""

    # 추가 옵션
    negative_prompt: str = ""
    aspect_ratio: str = "9:16"
    duration: int = 8

    def build(self) -> str:
        """최종 프롬프트 생성 (Directorial Paragraph 형식)"""
        parts = []

        # 1. 메인 비주얼 구성 (주제 + 동작 + 환경)
        main_visual = ""
        if self.subject:
            main_visual = f"A {self.style or 'cinematic'} shot of a {self.subject}"
            if self.environment:
                main_visual += f" in a {self.environment}"
            if self.action:
                main_visual += f", {self.action}"

        if main_visual:
            parts.append(main_visual + ".")

        # 2. 카메라 및 구도
        camera_prompt = CAMERA_MOVEMENTS.get(self.camera_movement, {}).get(
            "prompt", "static shot"
        )
        comp_prompt = COMPOSITIONS.get(self.composition, {}).get(
            "prompt", "medium shot"
        )
        parts.append(
            f"The camera performs a {camera_prompt} with {comp_prompt} framing."
        )

        # 3. 조명 및 기술 디테일
        mood_prompt = LIGHTING_MOODS.get(self.lighting_mood, {}).get(
            "prompt", "natural lighting"
        )
        parts.append(
            f"Lighting is {mood_prompt}, optimized for 4k photorealistic fidelity."
        )

        # 4. 텍스트 방지 강조
        parts.append("ZERO text, no watermarks, no typography on screen.")

        # 오디오 섹션
        audio_section = self._build_audio_section()

        # 최종 서술형 조합
        main_prompt = " ".join(parts)

        if audio_section:
            main_prompt += f"\n\n[AUDIO INTENT]\n{audio_section}"

        return main_prompt

    def _build_audio_section(self) -> str:
        """오디오 섹션 빌드 (Veo 3 가이드 형식)"""
        audio_parts = []

        # 대화 (따옴표 사용)
        if self.dialogue:
            audio_parts.append(f'- Dialogue: "{self.dialogue}"')

        # SFX (효과음)
        if self.sfx:
            sfx_text = ", ".join(self.sfx)
            audio_parts.append(f"- SFX: {sfx_text}")

        # 주변소음/앰비언트
        if self.ambient:
            audio_parts.append(f"- Ambient: {self.ambient}")

        # 배경음악
        audio_preset_prompt = AUDIO_PRESETS.get(self.audio_preset, {}).get("prompt", "")
        if audio_preset_prompt:
            audio_parts.append(f"- Music: {audio_preset_prompt}")

        return "\n".join(audio_parts)

    def with_product(
        self, product_name: str, description: str = "", category: str = ""
    ) -> "AdvancedPromptBuilder":
        """제품 촬영용 설정"""
        self.subject = f"A premium {product_name}"
        if category:
            self.subject += f" ({category})"

        # 설명이 있으면 환경이나 피사체 상세 정보로 활용
        if description:
            self.environment = (
                f"professional product photography setting reflecting: {description}"
            )
        else:
            self.environment = "modern minimalist studio with clean backdrop"

        self.lighting_mood = "studio"
        return self

    def with_marketing_hook(self, hook: str) -> "AdvancedPromptBuilder":
        """마케팅 훅 추가"""
        self.dialogue = hook
        return self

    def with_brand_kit(self, brand_kit: dict) -> "AdvancedPromptBuilder":
        """브랜드 킷 적용"""
        primary_color = brand_kit.get("primary_color")
        visual_vibes = brand_kit.get("visual_vibes", "premium")

        # 환경에 브랜드 색상/분위기 주입
        if primary_color:
            self.environment += f", subtly incorporating {primary_color} color palette"

        self.style = f"{visual_vibes} cinematic"
        return self

    def with_action_style(self, style: str) -> "AdvancedPromptBuilder":
        """동작 스타일 설정"""
        style_actions = {
            "reveal": "slowly revealing its key features with elegant presentation",
            "demo": "demonstrating its functionality step by step",
            "lifestyle": "being used naturally in everyday context",
            "unboxing": "being unboxed with anticipation and excitement",
            "comparison": "showing before and after transformation",
        }
        self.action = style_actions.get(style, style)
        return self

    @staticmethod
    def get_camera_movements() -> list[dict]:
        """사용 가능한 카메라 무브먼트 목록"""
        return [
            {
                "key": key,
                "name": val["name"],
                "name_ko": val["name_ko"],
                "description": val["description"],
            }
            for key, val in CAMERA_MOVEMENTS.items()
        ]

    @staticmethod
    def get_compositions() -> list[dict]:
        """사용 가능한 구도 목록"""
        return [
            {"key": key, "name": val["name"], "name_ko": val["name_ko"]}
            for key, val in COMPOSITIONS.items()
        ]

    @staticmethod
    def get_lighting_moods() -> list[dict]:
        """사용 가능한 조명/분위기 목록"""
        return [
            {"key": key, "name": val["name"], "name_ko": val["name_ko"]}
            for key, val in LIGHTING_MOODS.items()
        ]

    @staticmethod
    def get_audio_presets() -> list[dict]:
        """사용 가능한 오디오 프리셋 목록"""
        return [
            {"key": key, "name": val["name"], "name_ko": val["name_ko"]}
            for key, val in AUDIO_PRESETS.items()
        ]


class VeoClient:
    """Veo 비디오 생성 클라이언트"""

    def __init__(
        self,
        project_id: str,
        location: str,
        gcs_bucket_name: str,
        model_id: str,
        vision_model_id: str = "gemini-3-pro-preview",
    ) -> None:
        self._project_id = project_id
        self._location = location
        self._gcs_bucket_name = gcs_bucket_name
        self._model_id = model_id
        self._vision_model_id = vision_model_id
        self._client = None

    def _get_client(self):
        """Vertex AI GenAI 클라이언트 반환 (지연 초기화)"""
        if self._client is None:
            from google import genai

            self._client = genai.Client(
                vertexai=True,
                project=self._project_id,
                location=self._location,
            )
        return self._client

    def _pre_flight_safety_check(self, prompt: str) -> None:
        """Basic safety scan before sending prompt to Veo."""
        if not prompt:
            return

        blocked_terms = [
            "nsfw",
            "nude",
            "porn",
            "sex",
            "sexual",
            "gore",
            "blood",
            "hate",
            "violent",
            "violence",
        ]
        pattern = r"\b(" + "|".join(map(re.escape, blocked_terms)) + r")\b"
        if re.search(pattern, prompt, flags=re.IGNORECASE):
            raise VeoAPIError("Unsafe prompt content detected. Please revise.")

    def generate_video(
        self,
        prompt: str,
        duration_seconds: int = 8,
        resolution: str = "1080p",  # 품질 개선: 720p → 1080p
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> bytes | str:
        """텍스트 프롬프트로 비디오 생성"""
        # Veo 3.1 제한사항: 최대 8초 (4, 6, 8초 지원)
        if duration_seconds > 8:
            logger.warning(
                f"요청된 길이({duration_seconds}초)가 Veo 최대 길이(8초)를 초과하여 8초로 조정됩니다."
            )
            duration_seconds = 8

        log_api_start(
            "Veo Video Generation",
            f"Duration: {duration_seconds}s, Resolution: {resolution}",
        )
        start_time = time.time()

        try:
            self._pre_flight_safety_check(prompt)
            from google.genai.types import GenerateVideosConfig

            client = self._get_client()

            date_str = datetime.now().strftime("%Y%m%d")
            output_gcs_uri = f"gs://{self._gcs_bucket_name}/videos/{date_str}/"

            if progress_callback:
                progress_callback(
                    f"Veo API 요청 전송 중... ({duration_seconds}초, {resolution})", 10
                )

            operation = client.models.generate_videos(
                model=self._model_id,
                prompt=prompt,
                config=GenerateVideosConfig(  # type: ignore[call-arg]
                    aspect_ratio="9:16",
                    output_gcs_uri=output_gcs_uri,
                    duration_seconds=duration_seconds,
                    generate_audio=True,
                    number_of_videos=1,
                    resolution=resolution,
                    negative_prompt="text, watermark, typography, subtitles, logos, blurry, low quality, distorted, morphing, flickering, jittery, shaky, nsfw, violence, deformed, ugly, bad anatomy, unnatural motion, symbols, letters, numbers, static text",
                    person_generation="allow_adult",
                ),
            )

            result = self._handle_operation(
                operation, duration_seconds, progress_callback, output_gcs_uri
            )

            elapsed = time.time() - start_time
            log_api_end("Veo Video Generation", duration=elapsed)
            return result

        except Exception as e:
            log_error(f"비디오 생성 실패: {e}")
            raise VeoAPIError(f"비디오 생성 실패: {e}") from e

    def generate_video_from_image(
        self,
        image_bytes: bytes,
        prompt: str,
        duration_seconds: int = 8,
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> bytes | None:
        """이미지 기반 비디오 생성 (Image-to-Video)"""
        log_api_start("Veo I2V Generation", f"Duration: {duration_seconds}s")
        start_time = time.time()

        try:
            self._pre_flight_safety_check(prompt)
            from google.genai.types import GenerateVideosConfig

            client = self._get_client()

            # 이미지 파트 생성
            try:
                import io

                from PIL import Image

                image = Image.open(io.BytesIO(image_bytes))
            except Exception as img_err:
                log_error(f"이미지 처리 오류: {img_err}")
                raise VeoAPIError("유효하지 않은 이미지 데이터입니다.") from img_err

            date_str = datetime.now().strftime("%Y%m%d")
            output_gcs_uri = f"gs://{self._gcs_bucket_name}/videos_i2v/{date_str}/"

            if progress_callback:
                progress_callback("Veo Image-to-Video API 요청 중...", 10)

            enhanced_prompt = f"""
            {prompt}

            TRANSITION: Start from the provided image and naturally animate the scene.
            CAMERA: Smooth cinematic motion.
            QUALITY: 4k photorealistic, high fidelity.
            RESTRICTION: ZERO text, no watermarks, no typography on screen.
            NEGATIVE PROMPT: morphing, structural distortion, blurry, text artifacts, subtitles, logos.
            """.strip()

            operation = client.models.generate_videos(
                model=self._model_id,
                prompt=enhanced_prompt,
                config=GenerateVideosConfig(
                    input_images=[image],  # type: ignore[call-arg]
                    aspect_ratio="9:16",
                    output_gcs_uri=output_gcs_uri,
                    duration_seconds=duration_seconds,
                    generate_audio=True,
                    number_of_videos=1,
                    negative_prompt="watermarks, text, subtitles, low quality",
                    person_generation="allow_adult",
                ),
            )

            result = self._handle_operation(
                operation, duration_seconds, progress_callback, output_gcs_uri
            )

            elapsed = time.time() - start_time
            log_api_end("Veo I2V Generation", duration=elapsed)
            return result

        except Exception as e:
            log_error(f"이미지 기반 비디오 생성 실패: {e}")
            raise VeoAPIError(f"이미지 기반 비디오 생성 실패: {e}") from e

    def extend_video(
        self,
        video_uri: str,
        prompt: str,
        duration_seconds: int = 8,
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> bytes | str:
        """
        기존 비디오 연장 (Veo Video Extension)

        Args:
            video_uri: 원본 비디오의 GCS URI (gs://...)
            prompt: 연장될 부분에 대한 프롬프트
            duration_seconds: 연장할 길이 (기본 8초)
        """
        log_api_start(
            "Veo Video Extension",
            f"Source: {video_uri}, Ext Duration: {duration_seconds}s",
        )
        start_time = time.time()

        try:
            self._pre_flight_safety_check(prompt)
            from google.genai.types import GenerateVideosConfig, Video

            client = self._get_client()

            date_str = datetime.now().strftime("%Y%m%d")
            output_gcs_uri = f"gs://{self._gcs_bucket_name}/videos_ext/{date_str}/"

            if progress_callback:
                progress_callback("Veo Video Extension 요청 중...", 10)

            # GCS URI를 Video 객체로 변환하여 입력 비디오로 사용
            # google.genai.types.Video 객체 생성 (uri 필수)
            input_video = Video(uri=video_uri)

            operation = client.models.generate_videos(
                model=self._model_id,
                prompt=prompt,
                video=input_video,  # Video 객체 전달
                config=GenerateVideosConfig(
                    aspect_ratio="9:16",
                    output_gcs_uri=output_gcs_uri,
                    duration_seconds=duration_seconds,
                    generate_audio=True,
                    number_of_videos=1,
                    negative_prompt="watermarks, text, subtitles, low quality, morphing",
                    person_generation="allow_adult",
                ),
            )

            result = self._handle_operation(
                operation, duration_seconds, progress_callback, output_gcs_uri
            )

            elapsed = time.time() - start_time
            log_api_end("Veo Video Extension", duration=elapsed)
            return result

        except Exception as e:
            log_error(f"비디오 연장 실패: {e}")
            raise VeoAPIError(f"비디오 연장 실패: {e}") from e

    def generate_multimodal_prompt(
        self,
        system_instruction: str,
        user_instruction: str,
        image_bytes: bytes,
    ) -> str:
        """
        Gemini 1.5 Pro Vision을 이용한 멀티모달 프롬프트 생성
        (썸네일 이미지 + 기획 의도 -> Veo 프롬프트)
        """
        log_llm_request(
            "Veo 멀티모달 프롬프트 생성",
            f"이미지 {len(image_bytes):,} bytes, 지시문 {len(user_instruction)}자",
        )
        log_api_start("Gemini Vision Analysis", "Prompt Generation")

        try:
            import io

            from PIL import Image

            client = self._get_client()

            # 이미지 파트
            image = Image.open(io.BytesIO(image_bytes))

            # 채팅/콘텐츠 생성 요청
            response = client.models.generate_content(
                model=self._vision_model_id,
                contents=[system_instruction, user_instruction, image],
            )

            result_text = response.text
            log_llm_response(
                "Veo 멀티모달 프롬프트 생성", f"응답 {len(result_text or '')}자"
            )
            log_api_end("Gemini Vision Analysis")
            return result_text.strip()

        except Exception as e:
            log_llm_fail("Veo 멀티모달 프롬프트 생성", str(e))
            log_error(f"멀티모달 프롬프트 생성 실패: {e}")
            # 실패 시 기본 텍스트 반환이 아닌 에러 전파 (상위에서 처리)
            raise VeoAPIError(f"Vision API 호출 실패: {e}") from e

    def _handle_operation(
        self, operation, duration_seconds, progress_callback, output_gcs_uri
    ):
        """비디오 생성 오퍼레이션 공통 처리"""
        if progress_callback:
            progress_callback("작업 시작됨", 20)

        client = self._get_client()
        max_wait = 180 if duration_seconds > 8 else 120
        waited = 0

        log_process("Veo Generating", 0, max_wait)

        while not operation.done and waited < max_wait:
            time.sleep(10)
            waited += 10
            # 백그라운드 체크 중 에러 발생 시 처리
            try:
                operation = client.operations.get(operation)
            except Exception as op_err:
                log_error(f"Operation 상태 확인 중 오류: {op_err}")
                # 상태 확인 실패해도 계속 대기해볼 수 있음 (일시적 오류일 수 있으므로)
                continue

            log_process("Veo Generating", waited, max_wait)

            if progress_callback:
                progress = min(20 + int((waited / max_wait) * 60), 80)
                progress_callback(f"생성 중... ({waited}초)", progress)

        if operation.done and operation.result:
            generated_videos = getattr(operation.result, "generated_videos", None)

            if not generated_videos or len(generated_videos) == 0:
                log_error("비디오 생성 완료되었으나 결과물이 없습니다.")
                return (
                    f"영상 생성 실패: 결과물이 없습니다.\n"
                    f"GCS에서 확인: {output_gcs_uri}"
                )

            video = generated_videos[0]
            video_uri = video.video.uri

            logger.info(f"비디오 생성 완료: {video_uri}")

            if progress_callback:
                progress_callback("비디오 다운로드 중...", 85)

            # GCS에서 다운로드
            try:
                from google.cloud import storage as gcs_storage

                download_start = time.time()
                gcs_client = gcs_storage.Client()
                path_parts = video_uri.replace("gs://", "").split("/", 1)
                bucket_name = path_parts[0]
                blob_path = path_parts[1] if len(path_parts) > 1 else ""

                bucket = gcs_client.bucket(bucket_name)
                blob = bucket.blob(blob_path)
                video_content = blob.download_as_bytes()

                # 임시 파일 삭제 (Clean up) - 사용자 요청으로 비활성화 (버킷 보존)
                # try:
                #     blob.delete()
                #     logger.info(f"임시 비디오 파일 삭제 완료: {video_uri}")
                # except Exception as del_err:
                #     logger.warning(f"임시 비디오 파일 삭제 실패 (무시됨): {del_err}")

                logger.info(f"비디오가 GCS에 보존되었습니다: {video_uri}")

                log_timing("Video Download", (time.time() - download_start) * 1000)

                if progress_callback:
                    progress_callback("비디오 생성 완료!", 100)

                return video_content

            except Exception as download_error:
                log_error(f"비디오 다운로드 오류: {download_error}")
                return (
                    f"영상 생성됨 (GCS): {video_uri}\n다운로드 오류: {download_error}"
                )

        return f"영상 생성 진행 중 (백그라운드)\nGCS에서 확인: {output_gcs_uri}"

    # === 상업용 프롬프트 템플릿 (Veo 3.1 최적화) ===
    PRODUCT_SHOT_TEMPLATE = """
A {product} sits on a rotating pedestal inside a dark studio.
High-key rim lighting highlights its contours while a spotlight from above reveals brand details.
Camera: slow 360° dolly-around (thats where the camera is), 24 fps, 16:9, 1080p.
Audio: cinematic bass hit followed by subtle ambient synth.
    """.strip()

    MARKETING_SHORT_TEMPLATE = """
Create a {duration}-second vertical (9:16) short-form marketing video.

SUBJECT: {product} - a premium {category} product
ACTION: Hook viewer in first 2 seconds → Demonstrate key benefit → Subtle call-to-action
STYLE: Film-like quality with slight grain, professional commercial look
MOOD: {mood}

CAMERA: {camera_motion} (thats where the camera is)
RESOLUTION: 1080p, 24fps

AUDIO: {audio_style}

HOOK TEXT (spoken in first 3 seconds): "{hook}"
    """.strip()

    def generate_marketing_prompt(
        self,
        product: dict,
        insights: dict,
        hook_text: str = "",
        duration_seconds: int = 8,
        video_mode: str = "marketing",  # "marketing" | "product_360"
    ) -> str:
        """마케팅 비디오 프롬프트 생성 (Veo 3.1 최적화)"""
        p_name = product.get("name", "제품")
        p_category = product.get("category", "생활용품")
        hook = insights.get("hook", hook_text) or f"{p_name}!"
        style = insights.get("style", "commercial")
        mood = insights.get("mood", "dramatic")

        # 스타일별 카메라 모션 및 오디오 매핑
        camera_motions = {
            "horror": "slow push-in with slight shake",
            "commercial": "smooth tracking shot with gentle zoom",
            "dramatic": "dynamic dolly movement with reveal",
            "calm": "static wide shot with subtle float",
        }
        audio_styles = {
            "horror": "tense ambient drone building to climax",
            "commercial": "upbeat modern electronic with positive energy",
            "dramatic": "cinematic orchestral swell",
            "calm": "soft ambient piano with nature sounds",
        }

        camera_motion = camera_motions.get(style, camera_motions["commercial"])
        audio_style = audio_styles.get(mood, audio_styles["dramatic"])

        # 360도 제품 샷 모드
        if video_mode == "product_360":
            return self.PRODUCT_SHOT_TEMPLATE.format(product=p_name)

        # 마케팅 숏폼 영상 모드 (기본)
        prompt = self.MARKETING_SHORT_TEMPLATE.format(
            duration=duration_seconds,
            product=p_name,
            category=p_category,
            mood=mood,
            camera_motion=camera_motion,
            audio_style=audio_style,
            hook=hook,
        )

        return prompt

    def get_available_motions(self) -> list[str]:
        """사용 가능한 카메라 모션 목록"""
        return CAMERA_MOTIONS

    def generate_multi_video_prompts(
        self,
        product: dict,
        base_hook: str,
        duration_seconds: int = 8,
    ) -> list[dict]:
        """3가지 스타일의 비디오 프롬프트 생성"""
        styles = [
            {
                "type": "공포형",
                "style": "horror",
                "mood": "urgent",
                "hook": f"😱 {base_hook}",
            },
            {
                "type": "정보형",
                "style": "commercial",
                "mood": "hopeful",
                "hook": f"💡 {base_hook}",
            },
            {
                "type": "유머형",
                "style": "commercial",
                "mood": "hopeful",
                "hook": f"😂 {base_hook}",
            },
        ]

        results = []
        for s in styles:
            insights = {"hook": s["hook"], "style": s["style"], "mood": s["mood"]}
            # 여기서 duration_seconds를 전달하여 적절한 템플릿 사용
            prompt = self.generate_marketing_prompt(
                product, insights, duration_seconds=duration_seconds
            )

            results.append(
                {
                    "type": s["type"],
                    "hook": s["hook"],
                    "prompt": prompt,
                    "duration": duration_seconds,
                }
            )

            logger.info(f"{s['type']} 영상 프롬프트 생성 완료")

        return results
