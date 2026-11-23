"""@example models_12_custom_catalog_json.py
Serialize models from a custom catalog.
"""

import json
from models_09_custom_catalog import coding_models

print(json.dumps([record.name for record in coding_models()], indent=2))