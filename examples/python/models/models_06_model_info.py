"""@example models_06_model_info.py

Typed catalog access."""

import json

from Hestia.models import get_model_info
from Hestia.types import AcceleratorType, ModelSize

info = get_model_info(AcceleratorType.NVIDIA_CUDA, ModelSize.SMALL)
print(json.dumps(info.to_dict(), indent=2))
print(json.dumps(info.get("tools"), indent=2))

everything = get_model_info()
print(len(everything))

tiny = get_model_info(size=ModelSize.TINY)
print(json.dumps([i.accelerator.value for i in tiny], indent=2))
