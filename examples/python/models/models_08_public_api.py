"""@example models_08_public_api.py

Top-level access and import boundary."""

import sys

import Hestia
from Hestia.models import get_model_info

print(Hestia.get_model_info is get_model_info)
print(any(name.startswith("Hestia.hardware") for name in sys.modules))  # False
