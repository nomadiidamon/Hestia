"""@example hardware_04_simulated_gpus_json.py
Serialize the simulated GPU profiles as JSON.
"""

import json

from hardware_03_simulated_gpus import profiles


if __name__ == "__main__":
    integrated, multiple = profiles()
    print(json.dumps({"integrated": integrated.to_dict(), "multiple": multiple.to_dict()}, indent=2))