"""@example run_models.py
Run the model examples.
"""

import sys
from pathlib import Path

from run_all import run_scripts


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    sys.exit(run_scripts(sorted((here / "models").rglob("*.py")), here))
