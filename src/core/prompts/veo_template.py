"""
Google Veo 3.1 Prompt Templates & Protocols
"""

# System Instructions for Gemini to act as Prompt Engineer
VEO_SYSTEM_PROMPT = """
### 🤖 Role & Persona
You are a **Senior Cinematic Director & Veo 3.1 Prompt Specialist**.
Your goal is to transform marketing hooks into visually stunning, photorealistic, and cinematic video descriptions.

### ⚠️ Critical Directives (Quality & Safety)
1. **Directorial Style:** Write cohesive, descriptive paragraphs. Do not just list features. Focus on lighting, camera movement (e.g., "dolly focus-in on a 85mm lens"), and atmospheric texture.
2. **Text-Free Zone:** AI video models struggle with text. Therefore, **Omit all on-screen text, logos, or watermarks** from the visual description. The video should tell the story through pure visual and audio elements.
3. **Generic Subjects:** Use general terms for brands/people (e.g., 'A premium glass bottle', 'An elegant athlete').
4. **Cinematic Sound (ASMR & Foley):** Describe rich audio-visual synchrony. Tie sound effects (SFX) to specific visual cues (e.g., "The metallic click of the cap aligns with a 65mm close-up"). Emphasize ASMR-like clarity for product textures—crisp, tactile, and immersive.

### ✅ Negative Design Protocol
Always include: 'text, watermark, font, typography, subtitles, branding, blurry, low resolution, morphing, distorted artifacts' in the conceptual negative space.
"""

# Option 1: Dual Phase (Extension Strategy)
TEMPLATE_DUAL_PHASE = """
[Directorial Script: Phase 1 (0s-8s)]
SCENE: {scene}.
SHOT: 9:16 Vertical. A {motion} shot using a cinematic lens with professional depth of field.
VISUALS: The {subject} is the primary focus. {action_hook}. As the scene progresses, {action_process} lead to a peak moment of {action_peak}.
LIGHTING: {lighting} with professional color grading ({style}).
ATMOSPHERE: Photorealistic, 4k High Fidelity. No on-screen text or watermarks.
SOUND: {sound}. {voice_over}

[Directorial Script: Phase 2 (Extension 8s-12s)]
*Init Image: Continuity from Phase 1*
ACTION: A smooth transition to a freeze-frame aesthetic with subtle lens flares. The {subject} is showcased in a hero-shot position. {brand_voice_over}.
"""

# Option 2: Single Phase (Standard)
TEMPLATE_SINGLE_PHASE = """
[Directorial Script: Standard Shot (0s-8s)]
A 9:16 vertical cinematic shot featuring {subject} in a {scene} setting.
CAMERA: {motion} framing with {style} aesthetic.
ACTION: {action_start} transitioning smoothly into {action_end}.
LIGHTING/MOOD: {lighting} creating a professional brand atmosphere.
TECHNICAL: Photorealistic details, 4k resolution. ZERO text, watermarks, or overlays.
AUDIO: {sound}. Voice-over: "{voice_over}"
"""


class VeoTemplateManager:
    """Veo 프롬프트 템플릿 관리자"""

    @staticmethod
    def get_system_prompt() -> str:
        return VEO_SYSTEM_PROMPT

    @staticmethod
    def get_template(mode: str = "single") -> str:
        if mode == "dual":
            return TEMPLATE_DUAL_PHASE
        return TEMPLATE_SINGLE_PHASE
