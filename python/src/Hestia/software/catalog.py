"""Configured command definitions for software inventory."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import re
from types import MappingProxyType
from typing import Callable


VersionParser = Callable[[str], str | None]


@dataclass(frozen=True)
class SoftwareCommand:
	"""Ordered executable names and an optional version probe."""

	executables: tuple[str, ...]
	version_args: tuple[str, ...] = ()
	version_parser: VersionParser | None = None

	def __post_init__(self) -> None:
		if isinstance(self.executables, str) or not self.executables or any(
			not isinstance(item, str) or not item.strip() or "/" in item or "\\" in item
			for item in self.executables
		):
			raise ValueError("Software executables must contain nonempty command names, not paths")
		if isinstance(self.version_args, str) or any(
			not isinstance(item, str) or not item for item in self.version_args
		):
			raise ValueError("Version arguments must be nonempty strings")
		if bool(self.version_args) != (self.version_parser is not None):
			raise ValueError("Version arguments and parser must be supplied together")
		if self.version_parser is not None and not callable(self.version_parser):
			raise TypeError("Version parser must be callable")
		object.__setattr__(self, "executables", tuple(self.executables))
		object.__setattr__(self, "version_args", tuple(self.version_args))


@dataclass(frozen=True)
class SoftwareDefinition:
	"""A tool identity, default command, and optional platform-specific commands."""

	name: str
	executables: tuple[str, ...]
	version_args: tuple[str, ...] = ()
	version_parser: VersionParser | None = None
	platform_commands: Mapping[str, SoftwareCommand] = field(default_factory=dict)

	def __post_init__(self) -> None:
		if not self.name.strip():
			raise ValueError("Software name must not be empty")
		command = SoftwareCommand(self.executables, self.version_args, self.version_parser)
		if not isinstance(self.platform_commands, Mapping):
			raise TypeError("Platform commands must be a mapping")
		if any(not isinstance(key, str) or not key or key != key.strip() for key in self.platform_commands):
			raise ValueError("Platform command keys must be nonempty sys.platform values")
		if any(not isinstance(value, SoftwareCommand) for value in self.platform_commands.values()):
			raise TypeError("Platform commands must be SoftwareCommand instances")
		object.__setattr__(self, "executables", command.executables)
		object.__setattr__(self, "version_args", command.version_args)
		object.__setattr__(self, "platform_commands", MappingProxyType(dict(self.platform_commands)))


def _parse_git(output: str) -> str | None:
	match = re.search(
		r"(?im)^git version\s+(\d+\.\d+(?:\.[a-zA-Z0-9.+-]+)?)(?: \(Apple Git-[^)]+\))?\s*$",
		output,
	)
	return match.group(1) if match else None


def _parse_python(output: str) -> str | None:
	match = re.search(r"(?im)^Python\s+(\d+\.\d+\.\d+(?:[a-zA-Z0-9.+-]*)?)\s*$", output)
	return match.group(1) if match else None


def _parse_ollama(output: str) -> str | None:
	match = re.search(r"(?im)^ollama version (?:is\s+)?(\d+\.\d+\.\d+[a-zA-Z0-9.+-]*)\s*$", output)
	return match.group(1) if match else None


SOFTWARE_CATALOG: tuple[SoftwareDefinition, ...] = (
	SoftwareDefinition("git", ("git",), ("--version",), _parse_git),
	SoftwareDefinition("python", ("python", "python3"), ("--version",), _parse_python),
	SoftwareDefinition("ollama", ("ollama",), ("--version",), _parse_ollama),
)
