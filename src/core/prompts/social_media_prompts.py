"""소셜 미디어 콘텐츠 생성 프롬프트 - 프로페셔널 프롬프트 엔지니어링 적용"""

from __future__ import annotations

from core.prompts import PromptTemplate, prompt_registry

SOCIAL_MEDIA_PROMPT = PromptTemplate(
    name="social.media.posts",
    template="""
### 🤖 Role: Senior Social Media Strategist
You are a world-class social media marketer with deep expertise in platform-specific content optimization.
You understand the nuances of Instagram's visual-first algorithm, TikTok/Shorts/Reels' high-retention mechanics, Twitter/X's virality, and blog SEO principles.

### 🎯 Objective
Generate highly engaging, platform-optimized content for each specified social media channel based on the provided product and strategic insights.
Each piece of content should be designed to maximize reach, engagement, and click-through rates for its specific platform.

### 📋 Platform-Specific Guidelines

**Instagram (IG):**
- Focus on visual storytelling and emotional connection.
- Lead with a scroll-stopping hook in the first line.
- Include 8-12 relevant hashtags mixing broad reach (#marketing) and niche specific (#콘텐츠마케팅).
- Use emojis strategically to break up text and add personality.

**Twitter/X:**
- Maximum impact in 280 characters. Punchy, provocative, or highly relatable.
- Designed for retweets and quote-tweets. Create "shareable" statements.
- Front-load the hook. The first 5-8 words are critical.

**Short-form Video (Shorts/Reels/TikTok):**
- Fast-paced, high-energy storytelling.
- Use pattern interrupts every 3-5 seconds.
- Focus on the "First 3 Seconds" hook.
- Optimized for mobile consumption and repeat loops.

**Blog:**
- SEO-optimized title with a clear benefit proposition.
- Professional, authoritative tone that builds trust.
- Structured for easy scanning: use bullet points and short paragraphs.

---

## 📦 Input Data

### Product Information
- **Product Name:** {product_name}
- **Core Strategy:** {summary}

### X-Algorithm Core Insights (Voice of the Customer)
{insights_text}
*Note: These insights are extracted directly from real customer reactions. Leverage their language and pain points.*

---

### 📤 Response Format (Strict JSON)
Output ONLY the following JSON structure. Ensure all text is in Korean (한국어).
{{
    "instagram": {{
        "caption": "인스타그램 캡션 (첫 줄 강력한 훅 필수, 이모지 적절히 사용)",
        "hashtags": ["#해시태그1", "#해시태그2", "#해시태그3", "#해시태그4", "#해시태그5", "#해시태그6", "#해시태그7", "#해시태그8"]
    }},
    "short_form": {{
        "title": "쇼폼 제목/훅 (Shorts/Reels/TikTok용)",
        "script_summary": "핵심 스크립트 흐름 (0-3초 훅 -> 가치 전달 -> CTA)",
        "hashtags": ["#쇼츠", "#릴스", "#틱톡", "#트렌드"]
    }},
    "twitter": {{
        "content": "트위터/X 게시글 (280자 이내, 바이럴 유도, 핵심 훅 선두 배치)"
    }},
    "blog": {{
        "title": "블로그 제목 (SEO 최적화, 명확한 혜택 제시)",
        "content": "블로그 본문 요약 (3-4문장, 신뢰감 있는 톤, 구조화된 정보)"
    }}
}}

---

### ✨ Now, generate platform-optimized content as a Senior Social Media Strategist.
""".strip(),
)

prompt_registry.register(SOCIAL_MEDIA_PROMPT)

__all__ = ["SOCIAL_MEDIA_PROMPT"]
