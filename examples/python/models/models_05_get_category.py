"""@example models_05_get_category.py

Read model lists by category."""

from Hestia.models import get_category, get_tier
from Hestia.types import AcceleratorType, ModelSize

tier = get_tier(AcceleratorType.NONE, ModelSize.TINY)

tools = get_category(tier, "tools")
unknown = get_category(tier, "nope")
print("Tool models: " + (", ".join(tools) or "none"))
print("Unknown category: " + (", ".join(unknown) or "none"))
