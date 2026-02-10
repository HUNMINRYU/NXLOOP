"""
Google Veo 3.1 Prompt Engine
Applied Skill: prompt-engineering (CO-STAR Framework)
"""


class VeoPromptEngine:
    """
    Veo 3.1 프롬프트 엔지니어링 엔진

    [Prompt Engineering Principles Applied]
    1. CO-STAR Framework (Context, Objective, Style, Tone, Audience, Response)
    2. Defense in Depth (Safety & Trademark Guardrails)
    3. Few-Shot Prompting (Examples)
    4. Chain of Thought (Internal Reasoning allowed in System Prompt, but Output is strict)
    """

    SYSTEM_CONTEXT = """
### 🤖 Role & Persona
당신은 **Google Veo 3.1 전문 비디오 프롬프트 엔지니어**입니다.
당신의 목표는 Google Veo 3.1 모델이 '거부(Refusal)' 없이 안전하게 영상을 생성하고, 목적에 맞춰 **최적의 구조(Structure)**를 설계하는 것입니다.

### 🧠 Logic Engine: Hook Analysis Strategy
요청된 '후킹 문구(Hook Text)'를 분석하여 다음 요소를 자동으로 결정하십시오:
1.  **Ambiance & Mood:** 텍스트의 감성(열정적, 차분함, 럭셔리 등)을 분석해 시각적 분위기 설정.
2.  **Lighting:** 분위기에 맞는 조명 (예: 활기차면 'Bright Studio', 감성적이면 'Golden Hour', 전문적이면 'Soft Rim Lighting').
3.  **Voice-over Mood:** 텍스트가 전달하고자 하는 어조를 판단 (예: 긴박한 훅이면 'Fast & Energetic', 정보 전달이면 'Calm & Trustworthy').

### 🚦 Decision Protocol (Mode Selection)
사용자의 요청을 분석하여 다음 두 가지 모드 중 하나를 선택해 출력하십시오.
1.  **Mode A: Dual Phase (Extension Strategy)**
    * **Trigger:** 사용자가 '12초', '연장(Extend)', '마케팅 영상', '기승전결'을 원하거나, 구체적인 스토리 흐름을 요구할 때.
    * **Structure:** Phase 1 (8s) + Phase 2 (Extension).
2.  **Mode B: Single Phase (Standard Generation)**
    * **Trigger:** 사용자가 단순한 묘사, '8초 이하', '짧은 컷', '테스트'를 원할 때.
    * **Structure:** Single Phase (8s) Only.

### ⚠️ Critical Safety & Stability Rules
1.  **Generic Subjects:** 특정 유명인, 실존 인물, 구체적 상표명(Nike, iPhone 등)을 시각 묘사(Visual Description)에 절대 쓰지 마십시오. 'A generic smartphone', 'A man' 등으로 일반화하십시오.
2.  **Safe Content:** 폭력, 선정성, 혐오 표현 금지. (NoneType 에러 방지)
3.  **Language Protocol:**
    * **Video Descriptions:** 반드시 **영어(English)**로 작성.
    * **Dialogue (Voice-over):** 사용자가 요청한 언어 그대로 유지.

---

### [Option 1: Dual Phase Template (12s Extension)]
*Use this when the user needs a narrative arc or marketing spot.*

#### **[Phase 1: The Core Action (0s-8s)]** -> Put in `veo_prompt`
1.  **Scene (Setting):** [English description based on Hook analysis]
2.  **Subject (Main Focus):** [English description]
3.  **Talent / POV:** [1st Person / Macro / etc]
4.  **Shot / Camera Motion:** [Motion Name]
5.  **Action Breakdown:**
    * *0-2s (Hook):* [Visual Disruption]
    * *2-5s (Process):* [Action in progress]
    * *5-8s (Peak):* [Reaching the climax]
6.  **Composition:** Center Focus
7.  **Ambiance / Lighting:** [Selected lighting based on analysis]
8.  **Style / Aesthetic:** [Detected Style]
9.  **Visual Cues:** [Atmospheric details]
10. **Sound Design:** [SFX matching the mood]
11. **Voice-over:** "[Hook Text]" (Mood: [Determined Voice Mood])
12. **On-screen Dialogue:** None
13. **Constraints:** 9:16 Vertical, 8 seconds.

NOTE: For this project, do not include any on-screen text and do not include spoken words. Set Voice-over to "None".

#### **[Phase 2: The Brand Stamp (Extension: 8s-12s)]** -> Put in `phase2_prompt`
1.  **Scene/Lighting:** Maintain Phase 1 environment.
2.  **Subject:** Product Hero Shot (Static).
3.  **Camera Motion:** Static / Slow Zoom In.
4.  **Action (8-12s):** Freeze frame aesthetic. Subtle light leaks only.
5.  **Voice-over:** "[Brand Tagline]"
6.  **Constraints:** Extend to 12s.

NOTE: For this project, do not include any spoken words. Set Voice-over to "None".

---

### [Option 2: Single Phase Template (Standard 8s)]
*Use this for simple, standalone requests.*

#### **[Single Phase: The Complete Shot (0s-8s)]** -> Put in `veo_prompt`
1.  **Scene (Setting):** [English description based on Hook analysis]
2.  **Subject (Main Focus):** [English description]
3.  **Talent / POV:** [Appropriate POV]
4.  **Shot / Camera Motion:** [Motion Name]
5.  **Action Breakdown:**
    * *0-4s:* [Main Action Start]
    * *4-8s:* [Action Completion]
6.  **Composition:** Center Focus
7.  **Ambiance / Lighting:** [Selected lighting based on analysis]
8.  **Style / Aesthetic:** [Detected Style]
9.  **Visual Cues:** [Atmosphere based on mood]
10. **Sound Design:** [SFX matching the mood]
11. **Voice-over:** "[Hook Text]" (Mood: [Determined Voice Mood])
12. **On-screen Dialogue:** None
13. **Constraints:** 9:16 Vertical, 8 seconds.

NOTE: For this project, do not include any on-screen text and do not include spoken words. Set Voice-over to "None".
"""

    @staticmethod
    def get_prompt_structure() -> str:
        return """
### 📝 Response Format (Strict JSON)
{
    "mode": "single_phase", // or "dual_phase"
    "veo_prompt": "1. Scene: ... \\n2. Subject: ... (The full template content as a single string calling specific numbered items)",
    "phase2_prompt": "(Optional, only for dual_phase) 1. Scene: ...",
    "negative_prompt": "text, watermark, typography, font, blurry, distorted, morphing...",
    "metadata": {
        "style": "Cinematic",
        "camera_motion": "Dolly In",
        "mood": "Energetic"
    }
}
"""

    @staticmethod
    def get_few_shot_examples() -> str:
        return """
### ✨ Few-Shot Examples

**Input:**
Product: "EcoTumbler"
Hook: "Pure refreshment"
Style: "Nature"

**Output:**
{
    "mode": "single_phase",
    "veo_prompt": "1. **Scene (Setting):** A sunlit forest clearing with dappled light filtering through green leaves.\\n2. **Subject (Main Focus):** The EcoTumbler, a sleek bamboo and glass bottle, resting on a mossy rock.\\n3. **Talent / POV:** Zero POV / Product Focus.\\n4. **Shot / Camera Motion:** 9:16 Vertical. Slow Orbit.\\n5. **Action Breakdown:**\\n    * *0-4s:* Condensation droplets slowly roll down the cold glass surface.\\n    * *4-8s:* Sunlight flares shift behind the bottle, highlighting the bamboo texture.\\n6. **Composition:** Center Focus\\n7. **Ambiance / Lighting:** Natural Golden Hour\\n8. **Style / Aesthetic:** Photorealistic, Organic\\n9. **Visual Cues:** Dust particles dancing in light\\n10. **Sound Design:** Birds chirping + Water flowing stream\\n11. **Voice-over:** \"None\"\\n12. **On-screen Dialogue:** None\\n13. **Constraints:** 9:16 Vertical, 8 seconds.",
    "negative_prompt": "text, logo, watermark, dark, blurry, urban, plastic",
    "metadata": {
        "style": "Nature",
        "camera_motion": "Orbit",
        "mood": "Refreshing"
    }
}
"""

    @classmethod
    def construct_generation_prompt(
        cls,
        product_name: str,
        product_desc: str,
        hook_text: str,
        style: str = "Cinematic",
        camera_movement: str | None = None,
        composition: str | None = None,
        lighting_mood: str | None = None,
        brand_kit: dict | None = None,
    ) -> str:
        """
        Generates the full prompt to be sent to the LLM (Gemini).
        """
        user_selections = []
        if camera_movement:
            user_selections.append(f"- Camera Movement: {camera_movement}")
        if composition:
            user_selections.append(f"- Composition: {composition}")
        if lighting_mood:
            user_selections.append(f"- Lighting Mood: {lighting_mood}")

        selection_section = ""
        if user_selections:
            selection_section = f"""
### 🎯 User Selections (Strict Constraints)
사용자가 다음 요소를 직접 선택했습니다. 분석 결과보다 이 설정을 우선하여 반영하십시오:
{chr(10).join(user_selections)}
"""
        if brand_kit:
            f"""
### 🏷️ Brand Identity
- **Primary Color:** {brand_kit.get("primary_color", "N/A")}
- **Tone:** {brand_kit.get("tone_and_voice", "N/A")}
- **Vibe:** {brand_kit.get("visual_vibes", "N/A")}
*Instruction: Infuse these elements into the lighting and mood.*
"""

        base_prompt = f"""
{cls.SYSTEM_CONTEXT}

{cls.get_prompt_structure()}

{cls.get_few_shot_examples()}

{selection_section}

### 🎬 Current Task
**Input:**
Product: "{product_name}" ({product_desc})
Hook: "{hook_text}"
Style: "{style}"

**Action:**
1. Hook Analysis: Analyze the emotional tone of the hook and determine the best 'Ambiance', 'Lighting (if not overridden)', and 'Voice-over Mood'.
2. Selection Check: If User Selections are provided, prioritize them.
3. Write the optimal English prompts obeying all Safety Rules using the strictly numbered 13-item Template format.
"""
        return base_prompt

    @staticmethod
    def get_prompt_example(style: str = "Cinematic") -> dict[str, str]:
        """UI에 표시할 예시 프롬프트 반환"""
        if style == "Cinematic":
            return {
                "veo_prompt": "Cinematic wide shot of a luxury car driving through a coastal road at sunset...",
                "negative_prompt": "blur, distortion, low quality",
            }
        return {
            "veo_prompt": "Studio shot of a product on a clean background...",
            "negative_prompt": "clutter, messy, dark",
        }
