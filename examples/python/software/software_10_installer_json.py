"""@example software_10_installer_json.py
Serialize the unsupported and authorized installation reports.
"""

import json
from software_02_installer import run_example

unsupported, report = run_example(show_text=False)
print(json.dumps({"unsupported": unsupported.to_dict(), "installation": report.to_dict()}, indent=2))