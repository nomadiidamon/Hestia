"""@example models_05_get_category.py

Read model lists by category."""

import json

from Hestia.models import get_category, get_tier
from Hestia.types import AcceleratorType, ModelSize

tier = get_tier(AcceleratorType.NONE, ModelSize.TINY)

print(json.dumps(get_category(tier, "tools"), indent=2))
print(json.dumps(get_category(tier, "nope"), indent=2))  # unknown categories return []
