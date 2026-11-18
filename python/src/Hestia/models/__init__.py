"""AI model catalog and metadata."""

from importlib import import_module

from .catalog import (
    KNOWN_CATEGORIES,
    MODEL_CATALOG,
    MODEL_DATABASE,
    TIER_FALLBACK_ORDER,
    TierEntry,
    TierMap,
    get_category,
    get_tier,
)
from .info import ModelInfo, get_model_info
from .model_catalog import ModelCatalog, ModelCatalogEntry, ModelRecord

__all__ = [
    "KNOWN_CATEGORIES",
    "MODEL_CATALOG",
    "MODEL_DATABASE",
    "TIER_FALLBACK_ORDER",
    "TierEntry",
    "TierMap",
    "ModelInfo",
    "ModelCatalog",
    "ModelCatalogEntry",
    "ModelRecord",
    "ModelRecommendation",
    "ModelRecommendationWeight",
    "ModelRecommender",
    "recommend_model",
    "get_category",
    "get_model_info",
    "get_tier",
]

_RECOMMENDATION_EXPORTS = {
    "ModelRecommendation", "ModelRecommendationWeight", "ModelRecommender", "recommend_model",
}


def __getattr__(name: str):
    if name not in _RECOMMENDATION_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(".model_recommender", __name__), name)
    globals()[name] = value
    return value
