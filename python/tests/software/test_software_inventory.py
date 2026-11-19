import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

import Hestia
from Hestia.software import (
	SOFTWARE_CATALOG,
	SoftwareCommand,
	SoftwareDefinition,
	SoftwareProfile,
	VersionProbeStatus,
	detect_software,
)
from Hestia.software import detection


@pytest.mark.parametrize(
	("platform", "alias", "args"),
	[("win32", "win-tool", ("-V",)), ("darwin", "mac-tool", ("version",)),
	 ("linux", "tool", ("--version",)), ("freebsd14", "tool", ("--version",))],
)
def test_platform_specific_commands_and_default_fallback(monkeypatch, tmp_path, platform, alias, args):
	monkeypatch.setattr(detection, "sys", SimpleNamespace(platform=platform))
	lookups = []
	path = str(tmp_path / "tool.exe")
	monkeypatch.setattr(detection.shutil, "which", lambda name: lookups.append(name) or path)
	calls = []

	def run(command, **kwargs):
		calls.append(command)
		return subprocess.CompletedProcess(command, 0, "version=4.2", "")

	monkeypatch.setattr(detection.subprocess, "run", run)
	catalog = (SoftwareDefinition(
		"tool", ("tool",), ("--version",), lambda output: "default",
		platform_commands={
			"win32": SoftwareCommand(("win-tool",), ("-V",), lambda output: output.split("=")[1]),
			"darwin": SoftwareCommand(("mac-tool",), ("version",), lambda output: output.split("=")[1]),
		},
	),)
	tool = detect_software(catalog).tools[0]
	assert lookups == [alias]
	assert calls == [[path, *args]]
	assert tool.version == ("4.2" if platform in ("win32", "darwin") else "default")
	assert tool.version_status is VersionProbeStatus.DETECTED


@pytest.mark.parametrize(
	("output", "expected", "status"),
	[(b"\x81\ntool 1.2.3\n", "1.2.3", VersionProbeStatus.DETECTED),
	 (b"\x81\nno version\n", None, VersionProbeStatus.UNKNOWN)],
)
def test_version_probe_tolerates_non_decodable_output(monkeypatch, output, expected, status):
	monkeypatch.setattr(detection.shutil, "which", lambda name: sys.executable)
	command = SoftwareDefinition(
		"tool", ("tool",),
		("-c", f"import sys; sys.stdout.buffer.write({output!r})"),
		lambda text: text.split()[-1] if text.split()[-1] == "1.2.3" else None,
	)
	tool = detect_software((command,)).tools[0]
	assert tool.version == expected
	assert tool.version_status is status


def test_platform_override_replaces_default_and_is_immutable(monkeypatch):
	platform_commands = {"win32": SoftwareCommand(("windows-tool",))}
	definition = SoftwareDefinition("tool", ("default-tool",), platform_commands=platform_commands)
	platform_commands.clear()
	with pytest.raises(TypeError):
		definition.platform_commands["linux"] = SoftwareCommand(("linux-tool",))
	monkeypatch.setattr(detection, "sys", SimpleNamespace(platform="win32"))
	lookups = []
	monkeypatch.setattr(detection.shutil, "which", lambda name: lookups.append(name))
	tool = detect_software((definition,)).tools[0]
	assert not tool.present and tool.version_status is VersionProbeStatus.NOT_FOUND
	assert lookups == ["windows-tool"]


def test_inventory_uses_ordered_aliases_and_keeps_missing_and_duplicate_paths(monkeypatch, tmp_path):
	path = str(tmp_path / "shared")
	lookups = []

	def which(name):
		lookups.append(name)
		return path if name in {"second", "shared"} else None

	monkeypatch.setattr(detection.shutil, "which", which)
	catalog = (
		SoftwareDefinition("one", ("first", "second", "ignored")),
		SoftwareDefinition("missing", ("absent",)),
		SoftwareDefinition("two", ("shared",)),
	)
	profile = detect_software(catalog)
	assert [tool.name for tool in profile.tools] == ["one", "missing", "two"]
	assert lookups == ["first", "second", "absent", "shared"]
	assert [tool.executable_path for tool in profile.tools] == [path, None, path]
	assert [tool.present for tool in profile.tools] == [True, False, True]
	assert [tool.version_status for tool in profile.tools] == [
		VersionProbeStatus.NOT_SUPPORTED, VersionProbeStatus.NOT_FOUND, VersionProbeStatus.NOT_SUPPORTED,
	]
	assert json.loads(json.dumps(profile.to_dict()))["tools"][1]["version_status"] == "not_found"


def test_inventory_runs_only_configured_probe_with_timeout_and_stderr(monkeypatch, tmp_path):
	path = str(tmp_path / "tool.exe")
	monkeypatch.setattr(detection.shutil, "which", lambda name: path)
	calls = []

	def run(args, **kwargs):
		calls.append((args, kwargs))
		return subprocess.CompletedProcess(args, 0, stdout="", stderr="tool version 3.2.1")

	monkeypatch.setattr(detection.subprocess, "run", run)
	catalog = (SoftwareDefinition("tool", ("tool",), ("--version",), lambda output: output.split()[-1]),)
	tool = detect_software(catalog, timeout_seconds=2).tools[0]
	assert tool.version == "3.2.1"
	assert tool.version_status is VersionProbeStatus.DETECTED
	assert calls == [([path, "--version"], {
		"capture_output": True, "text": True, "stdin": subprocess.DEVNULL,
		"errors": "replace", "timeout": 2, "check": False,
	})]

	tool = detect_software(catalog, probe_versions=False).tools[0]
	assert tool.version_status is VersionProbeStatus.NOT_CHECKED
	assert len(calls) == 1


@pytest.mark.parametrize(
	("outcome", "expected"),
	[
		(subprocess.TimeoutExpired("tool", 1), VersionProbeStatus.TIMED_OUT),
		(OSError("cannot launch"), VersionProbeStatus.FAILED),
		(UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid"), VersionProbeStatus.FAILED),
		(subprocess.CompletedProcess([], 3, "", ""), VersionProbeStatus.FAILED),
		(subprocess.CompletedProcess([], 0, "unrecognized", ""), VersionProbeStatus.UNKNOWN),
	],
)
def test_probe_failure_retains_present_path(monkeypatch, tmp_path, outcome, expected):
	path = str(tmp_path / "tool.exe")
	monkeypatch.setattr(detection.shutil, "which", lambda name: path)

	def run(*args, **kwargs):
		if isinstance(outcome, Exception):
			raise outcome
		return outcome

	monkeypatch.setattr(detection.subprocess, "run", run)
	catalog = (SoftwareDefinition("tool", ("tool",), ("--version",), lambda output: None),)
	tool = detect_software(catalog).tools[0]
	assert tool.present and tool.executable_path == path
	assert tool.version is None and tool.version_status is expected
	assert tool.message


@pytest.mark.parametrize("parser", [lambda output: "", lambda output: 123, lambda output: 1 / 0])
def test_bad_version_parser_is_reported(monkeypatch, tmp_path, parser):
	monkeypatch.setattr(detection.shutil, "which", lambda name: str(tmp_path / "tool.exe"))
	monkeypatch.setattr(
		detection.subprocess, "run",
		lambda args, **kwargs: subprocess.CompletedProcess(args, 0, "output", ""),
	)
	tool = detect_software((SoftwareDefinition("tool", ("tool",), ("--version",), parser),)).tools[0]
	assert tool.present and tool.version_status is VersionProbeStatus.FAILED
	assert "parser failed" in tool.message


@pytest.mark.parametrize(
	("name", "output", "version"),
	[
		("git", "git version 2.47.1.windows.1\n", "2.47.1.windows.1"),
		("git", "git version 2.39.3 (Apple Git-146)\n", "2.39.3"),
		("python", "Python 3.14.0rc1\n", "3.14.0rc1"),
		("ollama", "Warning: server unavailable\nollama version is 0.6.1\n", "0.6.1"),
		("git", "git version unknown\n", None),
		("ollama", "model 1.2.3\n", None),
	],
)
def test_builtin_version_parsers(monkeypatch, tmp_path, name, output, version):
	definition = next(item for item in SOFTWARE_CATALOG if item.name == name)
	monkeypatch.setattr(detection.shutil, "which", lambda alias: str(tmp_path / "tool.exe"))
	monkeypatch.setattr(
		detection.subprocess, "run",
		lambda args, **kwargs: subprocess.CompletedProcess(args, 0, output, ""),
	)
	tool = detect_software((definition,)).tools[0]
	assert tool.version == version
	assert tool.version_status is (VersionProbeStatus.DETECTED if version else VersionProbeStatus.UNKNOWN)


def test_invalid_catalog_and_public_exports():
	with pytest.raises(ValueError, match="duplicate"):
		detect_software((SoftwareDefinition("Tool", ("a",)), SoftwareDefinition("tool", ("b",))))
	with pytest.raises(ValueError, match="supplied together"):
		SoftwareDefinition("tool", ("tool",), ("--version",))
	with pytest.raises(ValueError, match="not paths"):
		SoftwareDefinition("tool", ("bin/tool",))
	with pytest.raises(ValueError, match="sys.platform"):
		SoftwareDefinition("tool", ("tool",), platform_commands={" ": SoftwareCommand(("tool",))})
	with pytest.raises(TypeError, match="SoftwareCommand"):
		SoftwareDefinition("tool", ("tool",), platform_commands={"win32": "tool"})
	with pytest.raises(ValueError, match="finite and positive"):
		detect_software((), timeout_seconds=float("nan"))
	assert Hestia.detect_software is detect_software
	assert Hestia.SoftwareProfile is SoftwareProfile
	assert detect_software(()).tools == ()
