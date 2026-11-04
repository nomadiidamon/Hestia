"""@example models_01_enums.py

Enum values and lookup by value."""

from Hestia.types import AcceleratorType, ModelSize

print(AcceleratorType("nvidia_cuda"))
print([size.value for size in ModelSize])
