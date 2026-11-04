"""AI model catalog and metadata."""

from .catalog import (
    KNOWN_CATEGORIES,
    MODEL_DATABASE,
    TIER_FALLBACK_ORDER,
    TierEntry,
    TierMap,
    get_category,
    get_tier,
)
from .info import ModelInfo, get_model_info

__all__ = [
    "KNOWN_CATEGORIES",
    "MODEL_DATABASE",
    "TIER_FALLBACK_ORDER",
    "TierEntry",
    "TierMap",
    "ModelInfo",
    "get_category",
    "get_model_info",
    "get_tier",
]
