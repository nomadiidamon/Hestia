"""@example models_04_tier_fallback.py

Missing tiers fall back to a smaller tier or to CPU."""

from Hestia.models import MODEL_DATABASE, get_tier
from Hestia.types import AcceleratorType, ModelSize

# Intel has no XLARGE entry, so the LARGE entry is returned.
intel = get_tier(AcceleratorType.INTEL_ONEAPI, ModelSize.XLARGE)
print(intel is MODEL_DATABASE[AcceleratorType.INTEL_ONEAPI][ModelSize.LARGE])

# An accelerator with no catalog data falls back to CPU MEDIUM.
hexagon = get_tier(AcceleratorType.QUALCOMM_HEXAGON, ModelSize.TINY)
print(hexagon is MODEL_DATABASE[AcceleratorType.NONE][ModelSize.MEDIUM])
