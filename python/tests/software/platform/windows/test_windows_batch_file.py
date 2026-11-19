import os

import pytest

from Hestia.software import SoftwareDefinition, VersionProbeStatus, detect_software
from Hestia.software import detection


@pytest.mark.skipif(os.name != "nt", reason="Windows batch handling")
def test_windows_batch_file_is_not_executed(monkeypatch, tmp_path):
    path = str(tmp_path / "tool.cmd")
    monkeypatch.setattr(detection.shutil, "which", lambda name: path)

    def fail_run(*args, **kwargs):
        pytest.fail("Batch files must not be executed")

    monkeypatch.setattr(detection.subprocess, "run", fail_run)
    tool = detect_software((
        SoftwareDefinition("tool", ("tool",), ("--version",), lambda output: output),
    )).tools[0]
    assert tool.present and tool.executable_path == path
    assert tool.version_status is VersionProbeStatus.NOT_SUPPORTED
