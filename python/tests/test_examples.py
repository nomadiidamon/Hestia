"""Run every example script and require a clean exit."""

import os
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "python" / "src"
EXAMPLES = sorted((ROOT / "examples" / "python").rglob("*.py"))

FORMAT_PAIRS = [
    ("hardware/hardware_02_report.py", "hardware/hardware_01_profile.py"),
    ("hardware/hardware_03_simulated_gpus.py", "hardware/hardware_04_simulated_gpus_json.py"),
    ("models/models_01_enums.py", "models/models_13_enums_json.py"),
    ("models/models_05_get_category.py", "models/models_10_category_json.py"),
    ("models/models_06_model_info.py", "models/models_11_model_info_json.py"),
    ("models/models_09_custom_catalog.py", "models/models_12_custom_catalog_json.py"),
    ("recommendations/recommendation_01_basic.py", "recommendations/recommendation_03_basic_json.py"),
    ("recommendations/recommendation_02_constraints.py", "recommendations/recommendation_04_constraints_json.py"),
    ("software/software_01_dependency_checks.py", "software/software_09_dependency_checks_json.py"),
    ("software/software_02_installer.py", "software/software_10_installer_json.py"),
    ("software/software_03_doctor.py", "software/software_11_doctor_json.py"),
    ("software/software_04_detection.py", "software/software_05_profile.py"),
    ("software/software_06_catalog.py", "software/software_08_catalog_json.py"),
    ("cli/cli_02_report_text.py", "cli/cli_01_report_json.py"),
]


@pytest.mark.parametrize(("text_example", "json_example"), FORMAT_PAIRS)
def test_example_formats_are_separate(text_example, json_example):
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(SRC), os.environ.get("PYTHONPATH", "")])}
    directory = ROOT / "examples" / "python"
    outputs = []
    for example in (text_example, json_example):
        result = subprocess.run(
            [sys.executable, str(directory / example)], capture_output=True, text=True, timeout=60, env=env,
        )
        assert result.returncode == 0, result.stderr
        outputs.append(result.stdout)
    assert json.loads(outputs[1]) is not None
    with pytest.raises(json.JSONDecodeError):
        json.loads(outputs[0])
    assert not any(line.strip() in ("{", "[") for line in outputs[0].splitlines())


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_example_runs(example):
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(SRC), os.environ.get("PYTHONPATH", "")])}
    result = subprocess.run(
        [sys.executable, str(example)], capture_output=True, text=True, timeout=120, env=env
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("area", ["hardware", "models", "recommendations", "software"])
def test_area_runner_only_runs_its_examples_and_reports_failures(tmp_path, area):
    examples = ROOT / "examples" / "python"
    shutil.copy(examples / "run_all.py", tmp_path)
    shutil.copy(examples / f"run_{area}.py", tmp_path)
    directory = tmp_path / area
    directory.mkdir()
    (directory / "01_fail.py").write_text("print('first example'); raise SystemExit(3)\n", encoding="utf-8")
    (directory / "02_pass.py").write_text("print('second example')\n", encoding="utf-8")
    nested = directory / "nested"
    nested.mkdir()
    (nested / "example.py").write_text("print('nested example')\n", encoding="utf-8")
    other = tmp_path / "other"
    other.mkdir()
    (other / "example.py").write_text("print('unexpected example')\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(tmp_path / f"run_{area}.py")], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 1
    assert "first example" in result.stdout
    assert "second example" in result.stdout
    assert "nested example" in result.stdout
    assert "unexpected example" not in result.stdout
    assert "Ran 3 scripts, 1 failed" in result.stdout


def test_all_runner_only_runs_area_runners(tmp_path):
    shutil.copy(ROOT / "examples" / "python" / "run_all.py", tmp_path)
    (tmp_path / "run_a.py").write_text("print('area a')\n", encoding="utf-8")
    (tmp_path / "run_b.py").write_text("print('area b'); raise SystemExit(2)\n", encoding="utf-8")
    directory = tmp_path / "hardware"
    directory.mkdir()
    (directory / "example.py").write_text("print('unexpected direct example')\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(tmp_path / "run_all.py")], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 1
    assert "area a" in result.stdout and "area b" in result.stdout
    assert "unexpected direct example" not in result.stdout
    assert "Ran 2 scripts, 1 failed" in result.stdout


def test_area_runner_reports_missing_examples(tmp_path):
    examples = ROOT / "examples" / "python"
    shutil.copy(examples / "run_all.py", tmp_path)
    shutil.copy(examples / "run_models.py", tmp_path)
    result = subprocess.run(
        [sys.executable, str(tmp_path / "run_models.py")], capture_output=True, text=True, timeout=10
    )
    assert result.returncode != 0
    assert "No scripts found" in result.stderr


@pytest.mark.parametrize("area", ["hardware", "models", "recommendations", "software"])
@pytest.mark.parametrize("extension", ["bat", "sh"])
def test_area_wrapper_sets_import_path_and_propagates_exit(tmp_path, area, extension):
    if extension == "bat" and os.name != "nt":
        pytest.skip("Batch files require Windows")
    shell = shutil.which("sh") if extension == "sh" else os.environ.get("COMSPEC")
    if shell is None:
        pytest.skip(f"No shell available for {extension}")

    scripts = tmp_path / "python" / "scripts"
    scripts.mkdir(parents=True)
    wrapper = scripts / f"run_{area}_examples.{extension}"
    shutil.copy(ROOT / "python" / "scripts" / wrapper.name, wrapper)
    source = tmp_path / "python" / "src"
    source.mkdir()
    (source / "example_runner_test_marker.py").write_text("value = 7\n", encoding="utf-8")
    examples = tmp_path / "examples" / "python"
    examples.mkdir(parents=True)
    (examples / f"run_{area}.py").write_text(
        "import example_runner_test_marker\n"
        "print('wrapper ran')\n"
        "raise SystemExit(example_runner_test_marker.value)\n",
        encoding="utf-8",
    )
    command = [shell, "/d", "/c", str(wrapper)] if extension == "bat" else [shell, str(wrapper)]
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        command, input="\n", capture_output=True, text=True, timeout=20, cwd=tmp_path, env=env
    )
    assert result.returncode == 7, result.stderr
    assert "wrapper ran" in result.stdout


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


def test_constrained_recommendation_example_indents_reasoning():
    example = ROOT / "examples" / "python" / "recommendations" / "recommendation_02_constraints.py"
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(SRC), os.environ.get("PYTHONPATH", "")])}
    result = subprocess.run(
        [sys.executable, str(example)], capture_output=True, text=True, timeout=60, env=env
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    reasoning = lines[lines.index("Reasoning:") + 1:]
    assert len(reasoning) > 1
    assert all(line.startswith("  - ") for line in reasoning)


def test_live_recommendation_example_formats_model_lists_and_reasoning():
    example = ROOT / "examples" / "python" / "recommendations" / "recommendation_01_basic.py"
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(SRC), os.environ.get("PYTHONPATH", "")])}
    result = subprocess.run(
        [sys.executable, str(example)], capture_output=True, text=True, timeout=60, env=env
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert "[REC] Model Recommendation" in lines
    labels = [label for label in ("General:", "Thinking:", "Tool use:", "Vision:") if label in lines]
    if not labels:
        assert "Models: none" in lines
    for label in labels:
        assert lines[lines.index(label) + 1].startswith("  - ")

    reasoning = lines[lines.index("Reasoning:") + 1:]
    assert len(reasoning) > 1
    assert all(line.startswith("  - ") for line in reasoning)


def test_timed_install_example_reports_every_fraction(monkeypatch):
    path = ROOT / "examples" / "python" / "software" / "software_07_install_progress.py"
    spec = importlib.util.spec_from_file_location("install_progress_example", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    delays = []
    monkeypatch.setattr(module.time, "sleep", delays.append)
    events = []
    backend = module.SimulatedBackend()
    result = backend.install(
        type("Request", (), {"target": "demo"})(),
        timeout_seconds=30,
        report_progress=lambda message, fraction: events.append((message, fraction)),
    )
    assert sum(delays) == 15
    assert [fraction for _, fraction in events] == [second / 15 for second in range(1, 16)]
    assert result.succeeded and backend.installed
