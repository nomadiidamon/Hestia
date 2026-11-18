"""@example run_software.py
Run the software examples.
"""

import sys
from pathlib import Path

from run_all import run_scripts


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    sys.exit(run_scripts(sorted((here / "software").rglob("*.py")), here))
