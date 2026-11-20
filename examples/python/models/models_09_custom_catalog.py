"""@example models_09_custom_catalog.py
Extend the typed model catalog without changing the legacy dictionary.
"""

import json

from Hestia.models import MODEL_CATALOG, ModelCatalog, ModelCatalogEntry, ModelRecord
from Hestia.types import AcceleratorType, ModelSize

model = ModelRecord("example:1b", "example", 1.0)
custom_entry = ModelCatalogEntry(
    AcceleratorType.QUALCOMM_HEXAGON,
    ModelSize.TINY,
    {"models": (model,), "coding": (model,)},
    "q4_k_m", 1, 4096, "Advisory",
)
catalog = ModelCatalog([*MODEL_CATALOG.entries, custom_entry])
coding_models = catalog.resolve(
    AcceleratorType.QUALCOMM_HEXAGON, ModelSize.TINY
).categories["coding"]
print(json.dumps([record.name for record in coding_models], indent=2))
