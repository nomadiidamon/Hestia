"""@example hardware_01_profile.py
Detect hardware and inspect its serializable profile.
"""

import json

import Hestia


profile = Hestia.detect_hardware()
print(json.dumps(profile.to_dict(), indent=2))