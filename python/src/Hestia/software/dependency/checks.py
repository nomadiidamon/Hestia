"""Reusable read-only checks for common software requirements."""

from __future__ import annotations

import importlib.metadata
import os
import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from .core import CheckResult, Dependency, DependencyKind, DependencyStatus


class PythonPackageCheck:
	def __init__(self, distribution: str) -> None:
		self.distribution = distribution

	def __call__(self) -> CheckResult:
		try:
			version = importlib.metadata.version(self.distribution)
		except importlib.metadata.PackageNotFoundError:
			return CheckResult(
				DependencyStatus.MISSING,
				f"Python distribution is not installed: {self.distribution}",
			)
		return CheckResult(
			DependencyStatus.SATISFIED,
			f"Python distribution is installed: {self.distribution}",
			version=version,
		)


class CommandCheck:
	"""Check a configured command; optionally run fixed version arguments."""

	def __init__(
		self,
		command: str,
		*,
		version_args: tuple[str, ...] = (),
		version_parser: Callable[[str], str | None] | None = None,
		timeout_seconds: float = 5.0,
	) -> None:
		if timeout_seconds <= 0:
			raise ValueError("timeout_seconds must be positive")
		self.command = command
		self.version_args = version_args
		self.version_parser = version_parser
		self.timeout_seconds = timeout_seconds

	def __call__(self) -> CheckResult:
		path = shutil.which(self.command)
		if path is None:
			return CheckResult(
				DependencyStatus.MISSING,
				f"Command is not available on PATH: {self.command}",
			)
		if not self.version_args:
			return CheckResult(
				DependencyStatus.SATISFIED,
				f"Command is available: {self.command}",
				details={"path": path},
			)

		try:
			completed = subprocess.run(
				[path, *self.version_args],
				capture_output=True,
				text=True,
				timeout=self.timeout_seconds,
				check=False,
			)
		except subprocess.TimeoutExpired:
			return CheckResult(
				DependencyStatus.TIMED_OUT,
				f"Command check timed out: {self.command}",
				details={"path": path},
			)
		if completed.returncode != 0:
			return CheckResult(
				DependencyStatus.FAILED,
				f"Command check exited with status {completed.returncode}: {self.command}",
				details={"path": path},
			)

		output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
		version = self.version_parser(output) if self.version_parser is not None else None
		return CheckResult(
			DependencyStatus.SATISFIED,
			f"Command is available: {self.command}",
			version=version,
			details={"path": path},
		)


class PathCheck:
	def __init__(self, path: str | Path, *, directory: bool) -> None:
		self.path = Path(path)
		self.directory = directory

	def __call__(self) -> CheckResult:
		exists = self.path.is_dir() if self.directory else self.path.is_file()
		kind = "Directory" if self.directory else "File"
		status = DependencyStatus.SATISFIED if exists else DependencyStatus.MISSING
		message = f"{kind} exists: {self.path}" if exists else f"{kind} not found: {self.path}"
		return CheckResult(status, message, details={"path": str(self.path)})


class EnvironmentVariableCheck:
	def __init__(self, name: str, *, expected_value: str | None = None) -> None:
		self.name = name
		self.expected_value = expected_value

	def __call__(self) -> CheckResult:
		value = os.environ.get(self.name)
		if value is None:
			return CheckResult(
				DependencyStatus.MISSING,
				f"Environment variable is not set: {self.name}",
			)
		if self.expected_value is not None and value != self.expected_value:
			return CheckResult(
				DependencyStatus.INCOMPATIBLE,
				f"Environment variable does not match the expected value: {self.name}",
				details={"value": value},
			)
		return CheckResult(
			DependencyStatus.SATISFIED,
			f"Environment variable is set: {self.name}",
			details={"value": value},
		)


class ServiceCheck:
	"""Wrap an explicitly supplied probe, passing its required timeout."""

	def __init__(self, probe: Callable[[float], bool], *, timeout_seconds: float = 3.0) -> None:
		if timeout_seconds <= 0:
			raise ValueError("timeout_seconds must be positive")
		self.probe = probe
		self.timeout_seconds = timeout_seconds

	def __call__(self) -> CheckResult:
		if self.probe(self.timeout_seconds):
			return CheckResult(DependencyStatus.SATISFIED, "Service probe succeeded")
		return CheckResult(DependencyStatus.MISSING, "Service probe did not find the service")


class PythonPackageDependency(Dependency):
	def __init__(
		self,
		distribution: str,
		*,
		name: str | None = None,
		required: bool = True,
		version_specifier: str | None = None,
	) -> None:
		super().__init__(
			name or distribution,
			PythonPackageCheck(distribution),
			DependencyKind.PYTHON_PACKAGE,
			required,
			version_specifier,
		)


class SystemCommandDependency(Dependency):
	def __init__(
		self,
		command: str,
		*,
		name: str | None = None,
		required: bool = True,
		version_specifier: str | None = None,
		version_args: tuple[str, ...] = (),
		version_parser: Callable[[str], str | None] | None = None,
		timeout_seconds: float = 5.0,
	) -> None:
		super().__init__(
			name or command,
			CommandCheck(
				command,
				version_args=version_args,
				version_parser=version_parser,
				timeout_seconds=timeout_seconds,
			),
			DependencyKind.SYSTEM_COMMAND,
			required,
			version_specifier,
		)


class SystemLibraryDependency(Dependency):
	"""Dependency with an injected, platform-specific library probe."""

	def __init__(
		self,
		name: str,
		check: Callable[[], CheckResult],
		*,
		required: bool = True,
		version_specifier: str | None = None,
	) -> None:
		super().__init__(name, check, DependencyKind.SYSTEM_LIBRARY, required, version_specifier)


class DriverDependency(Dependency):
	"""Dependency with an injected driver probe for the target platform."""

	def __init__(
		self,
		name: str,
		check: Callable[[], CheckResult],
		*,
		required: bool = True,
		version_specifier: str | None = None,
	) -> None:
		super().__init__(name, check, DependencyKind.DRIVER, required, version_specifier)


class FileDependency(Dependency):
	def __init__(self, path: str | Path, *, name: str | None = None, required: bool = True) -> None:
		resolved_path = Path(path)
		super().__init__(
			name or str(resolved_path),
			PathCheck(resolved_path, directory=False),
			DependencyKind.FILE,
			required,
		)


class DirectoryDependency(Dependency):
	def __init__(self, path: str | Path, *, name: str | None = None, required: bool = True) -> None:
		resolved_path = Path(path)
		super().__init__(
			name or str(resolved_path),
			PathCheck(resolved_path, directory=True),
			DependencyKind.DIRECTORY,
			required,
		)


class EnvironmentVariableDependency(Dependency):
	def __init__(
		self,
		variable: str,
		*,
		name: str | None = None,
		required: bool = True,
		expected_value: str | None = None,
	) -> None:
		super().__init__(
			name or variable,
			EnvironmentVariableCheck(variable, expected_value=expected_value),
			DependencyKind.ENVIRONMENT_VARIABLE,
			required,
		)


class ServiceDependency(Dependency):
	def __init__(
		self,
		name: str,
		probe: Callable[[float], bool],
		*,
		required: bool = True,
		timeout_seconds: float = 3.0,
	) -> None:
		super().__init__(
			name,
			ServiceCheck(probe, timeout_seconds=timeout_seconds),
			DependencyKind.SERVICE,
			required,
		)


class CustomDependency(Dependency):
	def __init__(
		self,
		name: str,
		check: Callable[[], CheckResult],
		*,
		required: bool = True,
		version_specifier: str | None = None,
	) -> None:
		super().__init__(name, check, DependencyKind.CUSTOM, required, version_specifier)


def parse_first_version(output: str) -> str | None:
	"""Extract a PEP 440-like version token from explicitly requested output."""
	match = re.search(r"(?<![A-Za-z0-9])v?(\d+(?:\.\d+)+(?:[-+._][A-Za-z0-9.-]+)?)", output)
	return match.group(1) if match else None