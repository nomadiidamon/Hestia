"""@example models_03_get_tier.py

Resolve a tier for every accelerator and size."""

from Hestia.models import MODEL_DATABASE, get_tier
from Hestia.types import ModelSize

for accelerator in MODEL_DATABASE:
    for size in ModelSize:
        entry = get_tier(accelerator, size)
        print(f"{accelerator.value:14} {size.value:7} -> {entry['models'][0]}")
