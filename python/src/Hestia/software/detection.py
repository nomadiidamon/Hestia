"""Discover configured commands and optionally query their versions."""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence

from .catalog import SOFTWARE_CATALOG, SoftwareDefinition
from .profile import SoftwareProfile, SoftwareTool, VersionProbeStatus


def detect_software(
	catalog: Sequence[SoftwareDefinition] | None = None,
	*,
	probe_versions: bool = True,
	timeout_seconds: float = 5.0,
) -> SoftwareProfile:
	"""Discover configured tools in order; each version probe has its own timeout."""
	if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
		raise ValueError("timeout_seconds must be finite and positive")
	definitions = tuple(SOFTWARE_CATALOG if catalog is None else catalog)
	if any(not isinstance(item, SoftwareDefinition) for item in definitions):
		raise TypeError("Catalog entries must be SoftwareDefinition instances")
	names = [item.name.casefold() for item in definitions]
	if len(names) != len(set(names)):
		raise ValueError("Software catalog contains duplicate names")
	return SoftwareProfile(tuple(
		_detect_tool(item, probe_versions=probe_versions, timeout_seconds=timeout_seconds)
		for item in definitions
	))


def _detect_tool(
	definition: SoftwareDefinition, *, probe_versions: bool, timeout_seconds: float
) -> SoftwareTool:
	command = definition.platform_commands.get(sys.platform) or definition
	path = next((found for name in command.executables if (found := shutil.which(name))), None)
	if path is None:
		return SoftwareTool(definition.name, None, None, VersionProbeStatus.NOT_FOUND, "Command not found on PATH")
	path = os.path.abspath(path)
	if not probe_versions:
		return SoftwareTool(definition.name, path, None, VersionProbeStatus.NOT_CHECKED, "Version probing disabled")
	if not command.version_args or command.version_parser is None:
		return SoftwareTool(definition.name, path, None, VersionProbeStatus.NOT_SUPPORTED, "No version probe configured")
	if os.name == "nt" and os.path.splitext(path)[1].lower() in (".bat", ".cmd"):
		return SoftwareTool(definition.name, path, None, VersionProbeStatus.NOT_SUPPORTED, "Batch version probes are not supported")

	try:
		completed = subprocess.run(
			[path, *command.version_args], capture_output=True, text=True, errors="replace",
			stdin=subprocess.DEVNULL, timeout=timeout_seconds, check=False,
		)
	except subprocess.TimeoutExpired:
		return SoftwareTool(definition.name, path, None, VersionProbeStatus.TIMED_OUT, "Version probe timed out")
	except (OSError, UnicodeError) as error:
		return SoftwareTool(definition.name, path, None, VersionProbeStatus.FAILED, f"Version probe failed: {error}")
	if completed.returncode != 0:
		return SoftwareTool(
			definition.name, path, None, VersionProbeStatus.FAILED,
			f"Version probe exited with status {completed.returncode}",
		)
	output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
	try:
		version = command.version_parser(output)
		if version is not None and (not isinstance(version, str) or not version.strip()):
			raise ValueError("Version parser must return a nonempty string or None")
	except Exception as error:
		return SoftwareTool(definition.name, path, None, VersionProbeStatus.FAILED, f"Version parser failed: {error}")
	if version is None:
		return SoftwareTool(definition.name, path, None, VersionProbeStatus.UNKNOWN, "Version not recognized")
	return SoftwareTool(definition.name, path, version, VersionProbeStatus.DETECTED, "Version detected")
