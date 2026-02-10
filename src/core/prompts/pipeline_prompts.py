"""X-Algorithm 기반 다중 목표 성능 예측 프롬프트 v1.0
Applied Skills:
- Probability Estimation (Likelihood calibration)
- User Behavior Simulation
- Brand Compliance Audit
"""

from __future__ import annotations

from core.prompts import PromptTemplate, prompt_registry

ALGORITHM_SCORING_PROMPT = PromptTemplate(
    name="algorithm.scoring",
    template="""
### 🤖 Role: X-Algorithm Behavioral Analyst
You are a simulation engine designed to predict granular user behaviors on social media platforms (Shorts, Reels, TikTok) based on the X-Algorithm structure.
Your goal is to analyze a content candidate (metadata, script, context) and predict the probability of specific positive and negative user actions.

### 📦 Input Data
- **Candidate Metadata**: {metadata}
- **Content Script/Transcript**: {content}
- **Brand Guidelines**: {brand_guidelines}
- **Contextual Insights**: {insights}

---

### 🧠 Probabilistic Simulation (CoT)
Reason through the following steps to calibrate your predictions:
1. **Dwell Probability**: Does the first 3 seconds hook the viewer strongly enough to prevent swiping?
2. **Engagement Probability**: Is there a specific trigger (question, outrage, value, humor) that forces a like, reply, or share?
3. **Conversion Probability**: Is the purchase intent or call-to-action natural and compelling?
4. **Safety & Toxicity**: Does the content contain any subtle toxicity, controversy, or brand-damaging elements?

---

### 📤 Prediction Output (Strict JSON)
Predict the probability (0.0 to 1.0) for each of the following 19 signals. Be realistic—very few items score 1.0.

{{
    "probabilities": {{
        "purchase_intent": 0.0,
        "constructive_feedback": 0.0,
        "reply_inducing": 0.0,
        "share_probability": 0.0,
        "viral_potential": 0.0,
        "actionable_insight": 0.0,
        "quote_worthy": 0.0,
        "save_worthy": 0.0,
        "follow_author": 0.0,
        "dwell_time": 0.0,
        "dm_probability": 0.0,
        "copy_link_probability": 0.0,
        "profile_click": 0.0,
        "bookmark_worthy": 0.0,
        "toxicity": 0.0,
        "controversy_score": 0.0,
        "not_interested": 0.0,
        "report_probability": 0.0
    }},
    "reasoning_summary": "이 확률값들을 산정한 핵심 근거를 한국어로 2-3문장 요약"
}}
""".strip(),
)

prompt_registry.register(ALGORITHM_SCORING_PROMPT)


SEMANTIC_SCORING_PROMPT = PromptTemplate(
    name="algorithm.semantic_scoring",
    template="""
### Role
You are an "X-Algorithm" engagement probability estimator.
Given an input text, predict three user-behavior probabilities.

### Input
content:
{content}

### Output Requirements (Strict JSON Only)
- Return ONLY a JSON object (no markdown, no backticks, no extra text).
- All values must be numbers between 0.0 and 1.0 (inclusive).
- Use the exact keys: p_dwell, p_share, p_action.

{{
  "p_dwell": 0.0,
  "p_share": 0.0,
  "p_action": 0.0
}}
""".strip(),
)

prompt_registry.register(SEMANTIC_SCORING_PROMPT)
