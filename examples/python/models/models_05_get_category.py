"""@example models_05_get_category.py

Read model lists by category."""

from Hestia.models import get_category, get_tier
from Hestia.types import AcceleratorType, ModelSize

tier = get_tier(AcceleratorType.NONE, ModelSize.TINY)

print(get_category(tier, "tools"))
print(get_category(tier, "nope"))  # unknown categories return []
