"""Compatibility helpers and dictionary view of the typed model catalog.

Edit or extend catalog_data.py to maintain the built-in typed catalog. The
legacy MODEL_DATABASE snapshot does not control typed recommendations.
"""

from typing import Dict, List

from ..types import AcceleratorType, ModelSize
from .catalog_data import MODEL_CATALOG
from .model_catalog import DEFAULT_CATEGORIES

TierEntry = Dict[str, object]
TierMap = Dict[ModelSize, TierEntry]
KNOWN_CATEGORIES: List[str] = list(DEFAULT_CATEGORIES)
MODEL_DATABASE: Dict[AcceleratorType, TierMap] = MODEL_CATALOG.to_legacy()
TIER_FALLBACK_ORDER: List[ModelSize] = [
    ModelSize.LARGE, ModelSize.MEDIUM, ModelSize.SMALL, ModelSize.TINY,
]


def get_tier(accelerator: AcceleratorType, size: ModelSize) -> TierEntry:
    """Return a fresh dictionary for the resolved tier, falling back only downward."""
    return MODEL_CATALOG.resolve(accelerator, size).to_legacy()


def get_category(tier: TierEntry, category: str) -> List[str]:
    """Return an independent list, or an empty list for an absent category."""
    value = tier.get(category, [])
    if not isinstance(value, list) or not all(isinstance(model, str) for model in value):
        raise TypeError(f"Invalid catalog category {category!r}")
    return list(value)
