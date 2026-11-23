"""@example models_01_enums.py

Enum values and lookup by value."""

from Hestia.types import AcceleratorType, ModelSize

print(f"Accelerator: {AcceleratorType('nvidia_cuda').value}")
print("Model sizes: " + ", ".join(size.value for size in ModelSize))
