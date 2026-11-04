"""Legacy import path; use Hestia.models instead."""

from .models.catalog import (
    KNOWN_CATEGORIES,
    MODEL_DATABASE,
    TIER_FALLBACK_ORDER,
    TierEntry,
    TierMap,
    get_category,
    get_tier,
)
