"""@example models_02_catalog_entries.py

Inspect every catalog entry's keys."""

from Hestia.models import KNOWN_CATEGORIES, MODEL_DATABASE

required = (*KNOWN_CATEGORIES, "quantization", "batch_size", "context", "performance")

for accelerator, tiers in MODEL_DATABASE.items():
    for size, entry in tiers.items():
        missing = [key for key in required if key not in entry]
        print(f"{accelerator.value:14} {size.value:7} missing={missing}")
