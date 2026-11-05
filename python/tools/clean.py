"""Uninstall the editable Hestia package, then clean artifacts."""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
PYTHON_DIR = TOOLS_DIR.parent
PACKAGE_NAME = "hestia-system"
CLEAN_TOOLS = sorted(p.parent.name for p in TOOLS_DIR.glob("*/clean.py"))
ARTIFACT_DIRS = ["build", "dist", ".pytest_cache", ".mypy_cache", ".ruff_cache"]
ARTIFACT_FILES = ["project.ini"]
ARTIFACT_GLOBS = ["src/*.egg-info", "**/__pycache__"]


def find_main_artifacts() -> list:
    found = [PYTHON_DIR / name for name in ARTIFACT_DIRS if (PYTHON_DIR / name).exists()]
    found.extend(PYTHON_DIR / name for name in ARTIFACT_FILES if (PYTHON_DIR / name).is_file())
    for pattern in ARTIFACT_GLOBS:
        found.extend(PYTHON_DIR.glob(pattern))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="only list what would be removed; no uninstall, no prompt")
    parser.add_argument("-y", "--yes", action="store_true", help="skip the confirmation prompt")
    args = parser.parse_args()

    print("[Hestia] clean")
    artifacts = find_main_artifacts()
    print()
    print("[Hestia] main artifacts")
    for path in artifacts:
        print(f"  {path.relative_to(PYTHON_DIR)}")
    print()

    if not args.dry_run:
        print(f"Uninstalling editable package {PACKAGE_NAME!r}...")
        subprocess.call([sys.executable, "-m", "pip", "uninstall", "-y", PACKAGE_NAME])

    forwarded = [flag for flag, on in (("--dry-run", args.dry_run), ("--yes", args.yes)) if on]
    rc = 0
    for name in CLEAN_TOOLS:
        result = subprocess.call([sys.executable, str(TOOLS_DIR / name / "clean.py"), *forwarded])
        rc = rc or result

    if not args.dry_run and rc == 0:
        for path in artifacts:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
