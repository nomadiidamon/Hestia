"""Run the models tests and examples. Extra arguments go to pytest."""
import os
import subprocess
import sys
from pathlib import Path

PYTHON_DIR = Path(__file__).resolve().parents[2]
OUTPUT_FILE = PYTHON_DIR / "tests" / "test_output.txt"
TARGETS = ["tests/test_models.py", "tests/test_examples.py"]


def main() -> int:
    print("[Hestia.models] run tests")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *TARGETS, *sys.argv[1:]],
        cwd=PYTHON_DIR, capture_output=True, text=True,
    )
    print(proc.stdout + proc.stderr, end="")
    mode = "a" if os.environ.get("HESTIA_TEST_APPEND") else "w"
    with OUTPUT_FILE.open(mode, encoding="utf-8") as f:
        f.write(proc.stdout + proc.stderr)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
