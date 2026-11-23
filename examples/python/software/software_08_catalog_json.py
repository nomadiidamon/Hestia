"""@example software_08_catalog_json.py
Serialize the custom software catalog profile.
"""

import json
from software_06_catalog import detect_custom_catalog

print(json.dumps(detect_custom_catalog().to_dict(), indent=2))