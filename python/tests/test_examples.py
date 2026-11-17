"""Run every example script and require a clean exit."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "python" / "src"
EXAMPLES = sorted((ROOT / "examples" / "python").rglob("*.py"))


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_example_runs(example):
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(SRC), os.environ.get("PYTHONPATH", "")])}
    result = subprocess.run(
        [sys.executable, str(example)], capture_output=True, text=True, timeout=60, env=env
    )
    assert result.returncode == 0, result.stderr


def test_simulated_gpu_examples_show_both_scenarios():
    example = ROOT / "examples" / "python" / "hardware" / "hardware_03_simulated_gpus.py"
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(SRC), os.environ.get("PYTHONPATH", "")])}
    result = subprocess.run(
        [sys.executable, str(example)], capture_output=True, text=True, timeout=60, env=env
    )
    assert result.returncode == 0, result.stderr
    assert "Simulated integrated GPU fallback" in result.stdout
    assert "Simulated AMD Radeon Graphics" in result.stdout
    assert "n/a free" in result.stdout
    assert "Simulated multiple GPUs" in result.stdout
    assert "GPUs (2 detected)" in result.stdout
    assert "GPU-example-1" in result.stdout
    assert "GPU-example-2" in result.stdout
