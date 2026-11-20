"""@example cli_01_report_json.py

Run the installed-style CLI module and print a machine-readable system report.
"""

import subprocess
import sys


def main() -> None:
    subprocess.run(
        [sys.executable, "-m", "Hestia.cli", "report", "--json"],
        check=True,
    )


if __name__ == "__main__":
    main()
