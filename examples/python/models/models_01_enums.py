"""@example models_01_enums.py

Enum values and lookup by value."""

import json

from Hestia.types import AcceleratorType, ModelSize

print(AcceleratorType("nvidia_cuda"))
print(json.dumps([size.value for size in ModelSize], indent=2))
