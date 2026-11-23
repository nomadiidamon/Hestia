"""@example cli_02_report_text.py

Run the human-readable CLI report with terminal colors when available.
"""

import subprocess
import sys


def main() -> None:
    subprocess.run([sys.executable, "-m", "Hestia.cli", "report"], check=True)


if __name__ == "__main__":
    main()