"""CTR 예측 및 타이틀 최적화 프롬프트 - 프로페셔널 프롬프트 엔지니어링 v2.0
Applied Skills:
- Chain-of-Thought (Explicit Step-by-Step Reasoning)
- Few-Shot Learning (Dynamic Example Reference)
- Self-Consistency Verification
- Confidence Calibration
"""

from __future__ import annotations

from core.prompts import PromptTemplate, prompt_registry

CTR_PREDICTION_PROMPT = PromptTemplate(
    name="ctr.prediction",
    template="""
### 🤖 Role: Video Algorithm & CTR Optimization Expert
You are an elite video analytics specialist with a proven track record of boosting content performance across YouTube, Shorts, and Reels.
You understand the psychological triggers that drive clicks: curiosity gaps, urgency, social proof, and value propositions.

### 🎯 Objective
Analyze the provided video or short-form title for its Click-Through Rate (CTR) potential using a systematic, data-driven approach.
Provide actionable feedback and superior alternative titles that are scientifically optimized for maximum clicks.

### 📋 CTR Optimization Principles
1. **Curiosity Gap:** Titles that hint at valuable information without revealing everything perform best.
2. **Specificity:** Numbers and specific outcomes (e.g., "3 Days," "2x Results") increase trust and clicks.
3. **Emotional Trigger:** Words that evoke strong emotions (surprise, fear of missing out, desire) are powerful.
4. **Readability:** Keep titles under 60 characters when possible. Front-load the most compelling words.
5. **Pattern Interrupt:** Stand out from similar content in the niche to capture attention.
6. **A/B Mindset:** Always think in terms of testable variations with measurable differences.

---

## 📚 Few-Shot Examples (Reference Patterns)

### Example 1: Before → After (Beauty Category)
**Original:** "피부 관리 루틴 공유"
**Analysis:** Too generic, no specificity, no urgency
**Optimized:** "피부과 의사가 숨겨온 3단계 아침 루틴 (비용 0원)"
**Why Better:** Authority + Specificity + Value Proposition

### Example 2: Before → After (Tech Category)
**Original:** "노트북 구매 가이드"
**Analysis:** Information-focused, no curiosity gap, bland
**Optimized:** "2024년 노트북, 이거 모르고 사면 100만원 손해"
**Why Better:** Urgency + Loss Aversion + Specificity

---

## 📦 Input Data

### Target Title to Analyze
"{title}"

### Video Category
{category}

### X-Algorithm Core Insights (Customer Voice)
{insights_text}
*⚠️ CRITICAL: Use these insights to craft titles that directly address the audience's unmet needs and desires.*

---

### 🧠 Chain-of-Thought Analysis (Execute Step-by-Step)
Before providing your final analysis, reason through these steps INTERNALLY:

**Step 1: First Impression (0.5 seconds test)**
- What emotion does this title trigger immediately?
- Would I click if I saw this in my feed?

**Step 2: Structural Analysis**
- Character count (ideal: 40-60)
- Presence of numbers, brackets, or power words
- Front-loading of key value

**Step 3: Psychological Trigger Check**
- Curiosity Gap score (1-5)
- Urgency/FOMO level (1-5)
- Benefit clarity (1-5)

**Step 4: Competitive Differentiation**
- How does this stand out from typical titles in the category?
- What makes it memorable?

**Step 5: Insight Integration**
- Which customer pain points from X-Algorithm can strengthen this title?

---

### 📤 Response Format (Strict JSON)
Output ONLY the following JSON structure. Ensure all text is in Korean (한국어).
{{
    "chain_of_thought_summary": "2-3문장으로 위 분석 과정의 핵심 결론 요약",
    "analysis": {{
        "strengths": [
            {{
                "point": "강점 1",
                "explanation": "왜 이것이 강점인지 구체적 이유",
                "impact": "high | medium | low"
            }},
            {{
                "point": "강점 2",
                "explanation": "왜 이것이 강점인지 구체적 이유",
                "impact": "high | medium | low"
            }},
            {{
                "point": "강점 3",
                "explanation": "왜 이것이 강점인지 구체적 이유",
                "impact": "high | medium | low"
            }}
        ],
        "weaknesses": [
            {{
                "point": "개선점 1",
                "explanation": "왜 이것이 문제인지 + 고객 인사이트 기반 개선 방향",
                "improvement_hint": "구체적인 개선 힌트"
            }},
            {{
                "point": "개선점 2",
                "explanation": "왜 이것이 문제인지 + 고객 인사이트 기반 개선 방향",
                "improvement_hint": "구체적인 개선 힌트"
            }},
            {{
                "point": "개선점 3",
                "explanation": "왜 이것이 문제인지 + 고객 인사이트 기반 개선 방향",
                "improvement_hint": "구체적인 개선 힌트"
            }}
        ]
    }},
    "alternative_titles": [
        {{
            "title": "A/B 테스트용 대안 제목 1 (가장 추천)",
            "strategy": "이 제목에 적용된 전략 (예: Curiosity Gap + Specificity)",
            "rationale": "왜 이 제목이 원본보다 나은지 한 문장 설명",
            "expected_improvement": "+15~25% CTR 예상 근거"
        }},
        {{
            "title": "A/B 테스트용 대안 제목 2",
            "strategy": "적용된 전략",
            "rationale": "개선 이유",
            "expected_improvement": "예상 개선 폭"
        }},
        {{
            "title": "A/B 테스트용 대안 제목 3 (보수적 접근)",
            "strategy": "적용된 전략",
            "rationale": "개선 이유",
            "expected_improvement": "예상 개선 폭"
        }}
    ],
    "ctr_prediction": {{
        "original_score": "낮음 | 보통 | 높음 | 매우 높음",
        "best_alternative_score": "낮음 | 보통 | 높음 | 매우 높음",
        "confidence": "이 평가에 대한 신뢰도 (예: 75%)",
        "reasoning": "이 점수를 부여한 핵심 이유 (2-3문장)"
    }},
    "next_step": "이 분석 후 사용자가 즉시 취해야 할 액션 (한 문장)"
}}

---

### ✅ Self-Consistency Check (Execute Before Output)
- Are all three alternative titles meaningfully different from each other?
- Does each alternative apply a distinct optimization strategy?
- Is the confidence score calibrated realistically (not always "very high")?
- Have I integrated at least one X-Algorithm insight into the alternatives?

### ✨ Now, perform your expert CTR analysis.
""".strip(),
)

prompt_registry.register(CTR_PREDICTION_PROMPT)

__all__ = ["CTR_PREDICTION_PROMPT"]
