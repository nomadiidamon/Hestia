"""@example software_11_doctor_json.py
Serialize the doctor and delegated repair reports.
"""

import json
from software_03_doctor import run_example

before, repair, after = run_example(show_text=False)
print(json.dumps({"before": before.to_dict(), "repair": repair.to_dict(), "after": after.to_dict()}, indent=2))