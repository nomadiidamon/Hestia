"""@example models_13_enums_json.py
Serialize accelerator and model size values.
"""

import json
from Hestia.types import AcceleratorType, ModelSize

print(json.dumps({"accelerator": AcceleratorType("nvidia_cuda").value,
                  "model_sizes": [size.value for size in ModelSize]}, indent=2))