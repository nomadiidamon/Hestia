"""Remove hardware-related Python cache artifacts."""
import argparse
import shutil
import sys
from pathlib import Path

PYTHON_DIR = Path(__file__).resolve().parents[2]
ROOT = PYTHON_DIR.parent
DIRS = [
    PYTHON_DIR / "src" / "Hestia" / "hardware",
    PYTHON_DIR / "tests",
    ROOT / "examples" / "python" / "hardware",
    ROOT / "examples" / "python" / "recommendations",
]


def find_artifacts() -> list:
    found = [cache for base in DIRS for cache in base.rglob("__pycache__")]
    found.append(PYTHON_DIR / ".pytest_cache")
    found.append(PYTHON_DIR / "tests" / "test_output.txt")
    return [path for path in found if path.exists()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="only list what would be removed")
    parser.add_argument("-y", "--yes", action="store_true", help="skip the confirmation prompt")
    args = parser.parse_args()

    print("[Hestia.hardware] clean")
    artifacts = find_artifacts()
    for path in artifacts:
        print(f"  {path.relative_to(ROOT)}")
    if args.dry_run or not artifacts:
        return 0
    if not args.yes and input("Delete the above? [y/N] ").lower() != "y":
        print("Aborted.")
        return 1
    for path in artifacts:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main())