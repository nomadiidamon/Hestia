import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from Auctor.Stylus.Colors import Colors

import Hestia
from Hestia import cli
from Hestia._terminal import TTY
from Hestia.hardware import GPUInfo, HardwareProfile
from Hestia.types import AcceleratorType


def test_livy_records_existing_hestia_diagnostics_and_detaches(tmp_path, caplog):
    path = tmp_path / "hestia.log"
    livy = Hestia.configure_logging(path)
    try:
        with caplog.at_level(logging.DEBUG, logger="Hestia"):
            logging.getLogger("Hestia.hardware.detector").debug("probe failed: %s", "example")
        assert "probe failed: example" in caplog.text
        assert "[Hestia.hardware.detector] probe failed: example" in path.read_text()
    finally:
        Hestia.shutdown_logging()
    assert not livy.is_initialized()
    logging.getLogger("Hestia.hardware.detector").debug("after shutdown")
    assert "after shutdown" not in path.read_text()


def test_terminal_reports_use_color_when_supported(monkeypatch, capsys):
    monkeypatch.setattr(TTY, "supports_color", lambda self: True)
    Hestia.print_hardware_report(HardwareProfile())
    assert Colors.OKCYAN in capsys.readouterr().out


def test_report_colors_labels_but_not_values_and_preserves_layout(monkeypatch, capsys):
    profile = HardwareProfile(cpu_brand="Example CPU", gpus=[
        GPUInfo(0, "Example GPU", AcceleratorType.NVIDIA_CUDA, 8, 4),
    ])
    recommendation = Hestia.recommend_model(profile)
    monkeypatch.setattr(TTY, "supports_color", lambda self: False)
    Hestia.print_hardware_report(profile, recommendation)
    plain = capsys.readouterr().out
    monkeypatch.setattr(TTY, "supports_color", lambda self: True)
    Hestia.print_hardware_report(profile, recommendation)
    colored = capsys.readouterr().out
    assert re.sub(r"\x1b\[[0-9;]*m", "", colored) == plain
    for label in ("CPU:", "Cores:", "Frequency:", "RAM:", "Type:", "VRAM:",
                  "Platform:", "Python:", "Accelerator:", "Tier:", "Quantization:"):
        assert f"{Colors.OKCYAN}{label}{Colors.ENDC}" in colored
    assert f"{Colors.ENDC}       Example CPU" in colored
    assert f"{Colors.ENDC} Example GPU" in colored
    cli._print_software(SimpleNamespace(tools=[]))
    assert Colors.OKCYAN in capsys.readouterr().out


def test_json_remains_uncolored_when_color_is_supported(monkeypatch, capsys):
    monkeypatch.setattr(TTY, "supports_color", lambda self: True)
    monkeypatch.setattr(cli.Hestia, "detect_hardware", lambda: SimpleNamespace(to_dict=lambda: {"ok": True}))
    assert cli.main(["hardware", "--json"]) == 0
    output = capsys.readouterr().out
    assert "\x1b" not in output
    assert json.loads(output) == {"ok": True}


@pytest.mark.skipif(os.name == "nt", reason="requires a POSIX pseudo-terminal")
def test_cli_uses_color_with_a_real_terminal():
    import pty

    master, slave = pty.openpty()
    env = os.environ.copy()
    source = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = os.pathsep.join((source, env.get("PYTHONPATH", "")))
    try:
        result = subprocess.run(
            [sys.executable, "-m", "Hestia.cli", "software", "--no-version-probes"],
            stdout=slave, stderr=subprocess.PIPE, env=env, timeout=30,
        )
        os.close(slave)
        slave = -1
        output = os.read(master, 16384).decode()
        assert result.returncode == 0, result.stderr.decode()
        assert Colors.OKCYAN in output
        assert "Configured software" in output
    finally:
        os.close(master)
        if slave != -1:
            os.close(slave)