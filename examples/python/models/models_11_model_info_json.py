"""@example models_11_model_info_json.py
Serialize typed catalog information.
"""

import json
from Hestia.models import get_model_info
from Hestia.types import AcceleratorType, ModelSize

info = get_model_info(AcceleratorType.NVIDIA_CUDA, ModelSize.SMALL)
print(json.dumps({
    "info": info.to_dict(), "tools": info.get("tools"),
    "catalog_entries": len(get_model_info()),
    "tiny_accelerators": [item.accelerator.value for item in get_model_info(size=ModelSize.TINY)],
}, indent=2))