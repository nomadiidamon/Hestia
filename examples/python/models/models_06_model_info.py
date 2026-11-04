"""@example models_06_model_info.py

Typed catalog access."""

from Hestia.models import get_model_info
from Hestia.types import AcceleratorType, ModelSize

info = get_model_info(AcceleratorType.NVIDIA_CUDA, ModelSize.SMALL)
print(info.to_dict())
print(info.get("tools"))

everything = get_model_info()
print(len(everything))

tiny = get_model_info(size=ModelSize.TINY)
print([i.accelerator.value for i in tiny])
