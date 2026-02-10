"""
도메인 모델 패키지
모든 Pydantic 모델을 중앙 export
"""
from .chatbot import (
    ChatMessage,
    ChatSession,
)
from .marketing import (
    CompetitorAnalysis,
    ContentStrategy,
    HookingPoint,
    MarketingStrategy,
    MarketTrend,
    ShortformScenario,
    SNSCopy,
    TargetPersona,
)
from .naver import (
    CompetitorStats,
    NaverProduct,
    NaverSearchResult,
)
from .pipeline import (
    CollectedData,
    GeneratedContent,
    PipelineConfig,
    PipelineMetrics,
    PipelineProgress,
    PipelineResult,
    PipelineStep,
    UploadStatus,
)
from .product import (
    Product,
    ProductCatalog,
    ProductCategory,
)
from .youtube import (
    GainPoint,
    PainPoint,
    YouTubeComment,
    YouTubeSearchResult,
    YouTubeVideo,
)

__all__ = [
    # Chatbot
    "ChatMessage",
    "ChatSession",
    "CollectedData",
    "CompetitorAnalysis",
    "CompetitorStats",
    "ContentStrategy",
    "GainPoint",
    "GeneratedContent",
    "HookingPoint",
    "MarketTrend",
    "MarketingStrategy",
    # Naver
    "NaverProduct",
    "NaverSearchResult",
    "PainPoint",
    "PipelineConfig",
    "PipelineMetrics",
    "PipelineProgress",
    "PipelineResult",
    # Pipeline
    "PipelineStep",
    # Product
    "Product",
    "ProductCatalog",
    "ProductCategory",
    "SNSCopy",
    "ShortformScenario",
    # Marketing
    "TargetPersona",
    "UploadStatus",
    "YouTubeComment",
    "YouTubeSearchResult",
    # YouTube
    "YouTubeVideo",
]
