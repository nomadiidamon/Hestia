"""@example run_all.py

Run each area-specific Python example runner."""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run_scripts(scripts: list[Path], root: Path) -> int:
    """Run scripts in order, reporting every failure after all have run."""
    if not scripts:
        print(f"No scripts found under {root}", file=sys.stderr)
        return 1
    failed = []
    for index, script in enumerate(scripts, start=1):
        name = script.relative_to(root).as_posix()
        print("=" * 70)
        print(f"[{index}/{len(scripts)}] {name}")
        print("=" * 70, flush=True)
        result = subprocess.run([sys.executable, str(script)])
        if result.returncode != 0:
            failed.append(name)
            print(f"--- FAILED: {name} (exit code {result.returncode})", flush=True)
        print()

    print("=" * 70)
    print(f"Ran {len(scripts)} scripts, {len(failed)} failed")
    for name in failed:
        print(f"  FAILED: {name}")
    return 1 if failed else 0


def main() -> int:
    runners = sorted(path for path in HERE.glob("run_*.py") if path != Path(__file__).resolve())
    return run_scripts(runners, HERE)


if __name__ == "__main__":
    sys.exit(main())
