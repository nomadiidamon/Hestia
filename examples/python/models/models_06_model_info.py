"""@example models_06_model_info.py

Typed catalog access."""

from Hestia.models import get_model_info
from Hestia.types import AcceleratorType, ModelSize

info = get_model_info(AcceleratorType.NVIDIA_CUDA, ModelSize.SMALL)
print(f"Model tier: {info.accelerator.value} / {info.size.value}")
print(f"Quantization: {info.quantization}; context: {info.context:,}; performance: {info.performance}")
for category, models in info.categories.items():
	if models:
		print(f"{category}: {', '.join(models)}")
everything = get_model_info()
print(f"Catalog entries: {len(everything)}")

tiny = get_model_info(size=ModelSize.TINY)
print("Tiny accelerators: " + ", ".join(item.accelerator.value for item in tiny))
