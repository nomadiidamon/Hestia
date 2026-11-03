"""Uninstall the editable Hestia package, then clean artifacts."""
import argparse
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
PACKAGE_NAME = "Hestia"
CLEAN_TOOLS = ["Hestia"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="only list what would be removed; no uninstall, no prompt")
    parser.add_argument("-y", "--yes", action="store_true", help="skip the confirmation prompt")
    args = parser.parse_args()

    print("[Auctor] clean")
    if not args.dry_run:
        print(f"Uninstalling editable package {PACKAGE_NAME!r}...")
        subprocess.call([sys.executable, "-m", "pip", "uninstall", "-y", PACKAGE_NAME])

    forwarded = [flag for flag, on in (("--dry-run", args.dry_run), ("--yes", args.yes)) if on]
    rc = 0
    for name in CLEAN_TOOLS:
        result = subprocess.call([sys.executable, str(TOOLS_DIR / name / "clean.py"), *forwarded])
        rc = rc or result
    return rc


if __name__ == "__main__":
    sys.exit(main())
