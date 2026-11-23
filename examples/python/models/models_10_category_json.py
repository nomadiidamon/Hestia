"""@example models_10_category_json.py
Serialize model lists by category.
"""

import json
from Hestia.models import get_category, get_tier
from Hestia.types import AcceleratorType, ModelSize

tier = get_tier(AcceleratorType.NONE, ModelSize.TINY)
print(json.dumps({"tools": get_category(tier, "tools"), "unknown": get_category(tier, "nope")}, indent=2))