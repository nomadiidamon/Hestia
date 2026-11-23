"""@example software_09_dependency_checks_json.py
Serialize the read-only dependency report.
"""

import json
from software_01_dependency_checks import build_report

print(json.dumps(build_report().to_dict(), indent=2))