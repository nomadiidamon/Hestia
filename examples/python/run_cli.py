"""@example run_cli.py
Run the command-line interface examples.
"""

import sys
from pathlib import Path

from run_all import run_scripts


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    sys.exit(run_scripts(sorted((here / "cli").rglob("*.py")), here))
