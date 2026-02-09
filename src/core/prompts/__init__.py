"""프롬프트 템플릿/레지스트리"""
from __future__ import annotations


class PromptTemplate:
    def __init__(self, name: str, template: str, version: str = "v1") -> None:
        self.name = name
        self.template = template
        self.version = version

    def render(self, **kwargs) -> str:
        return self.template.format_map(kwargs)


class PromptRegistry:
    def __init__(self) -> None:
        self._templates: dict[str, PromptTemplate] = {}

    def register(self, template: PromptTemplate) -> None:
        self._templates[template.name] = template

    def get(self, name: str) -> PromptTemplate:
        if name not in self._templates:
            raise KeyError(f"등록되지 않은 프롬프트: {name}")
        return self._templates[name]


prompt_registry = PromptRegistry()

__all__ = ["PromptRegistry", "PromptTemplate", "prompt_registry"]

# 프롬프트 템플릿들은 각 모듈에서 prompt_registry.register(...)를 수행합니다.
# 이 패키지가 import될 때 등록이 누락되면 런타임에서 "등록되지 않은 프롬프트"가 발생하므로,
# 아래에서 모듈들을 명시적으로 import해 레지스트리를 채웁니다.
#
# NOTE: circular import를 피하기 위해 prompt_registry 정의 이후에 import합니다.
from . import (  # noqa: E402
    chatbot_prompts as _chatbot_prompts,
)
from . import (
    ctr_prediction_prompts as _ctr_prediction_prompts,
)
from . import (
    hydration_prompts as _hydration_prompts,
)
from . import (
    marketing_prompts as _marketing_prompts,
)
from . import (
    pipeline_prompts as _pipeline_prompts,
)
from . import (
    social_media_prompts as _social_media_prompts,
)
from . import (
    studio_prompts as _studio_prompts,
)
