"""Run the Hestia test suite. Extra arguments go to pytest."""
import os
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = TOOLS_DIR.parent / "tests" / "test_output.txt"
SUITES = ["Hestia"]


def main() -> int:
    print("[Hestia] run tests")
    OUTPUT_FILE.write_text("", encoding="utf-8")
    env = {**os.environ, "HESTIA_TEST_APPEND": "1"}
    rc = 0
    for name in SUITES:
        result = subprocess.call(
            [sys.executable, str(TOOLS_DIR / name / "run_tests.py"), *sys.argv[1:]], env=env
        )
        rc = rc or result
    return rc


if __name__ == "__main__":
    sys.exit(main())
