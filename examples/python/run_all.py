"""@example run_all.py

Runs every other Python example in order, labeling each one's output."""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
examples = sorted(p for p in HERE.rglob("*.py") if p != Path(__file__).resolve())

failed = []
for index, example in enumerate(examples, start=1):
    name = example.relative_to(HERE).as_posix()
    print("=" * 70)
    print(f"[{index}/{len(examples)}] {name}")
    print("=" * 70, flush=True)
    result = subprocess.run([sys.executable, str(example)])
    if result.returncode != 0:
        failed.append(name)
        print(f"--- FAILED: {name} (exit code {result.returncode})", flush=True)
    print()

print("=" * 70)
print(f"Ran {len(examples)} examples, {len(failed)} failed")
for name in failed:
    print(f"  FAILED: {name}")
sys.exit(1 if failed else 0)
