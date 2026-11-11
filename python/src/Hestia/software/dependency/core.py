"""Dependency specifications, results, and read-only check registration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Mapping, Protocol, Sequence

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version


class DependencyKind(str, Enum):
	PYTHON_PACKAGE = "python_package"
	SYSTEM_COMMAND = "system_command"
	COMMAND = "system_command"
	SYSTEM_LIBRARY = "system_library"
	DRIVER = "driver"
	FILE = "file"
	DIRECTORY = "directory"
	ENVIRONMENT_VARIABLE = "environment_variable"
	SERVICE = "service"
	CUSTOM = "custom"


class DependencyStatus(str, Enum):
	SATISFIED = "satisfied"
	MISSING = "missing"
	INCOMPATIBLE = "incompatible"
	FAILED = "failed"
	TIMED_OUT = "timed_out"
	UNKNOWN = "unknown"


@dataclass(frozen=True)
class CheckResult:
	status: DependencyStatus
	message: str
	version: str | None = None
	details: Mapping[str, str] = field(default_factory=dict)


class DependencyCheck(Protocol):
	def __call__(self) -> CheckResult: ...


@dataclass(frozen=True)
class Dependency:
	name: str
	check: DependencyCheck
	kind: DependencyKind = DependencyKind.CUSTOM
	required: bool = True
	version_specifier: str | None = None

	def __post_init__(self) -> None:
		if not self.name.strip():
			raise ValueError("Dependency name must not be empty")
		if self.version_specifier is not None:
			try:
				SpecifierSet(self.version_specifier)
			except InvalidSpecifier as error:
				raise ValueError(f"Invalid version specifier: {self.version_specifier}") from error


DependencySpec = Dependency


@dataclass(frozen=True)
class DependencyResult:
	name: str
	kind: DependencyKind
	status: DependencyStatus
	required: bool
	message: str
	version: str | None = None
	version_specifier: str | None = None
	details: Mapping[str, str] = field(default_factory=dict)

	@property
	def is_satisfied(self) -> bool:
		return self.status is DependencyStatus.SATISFIED

	@property
	def is_blocking(self) -> bool:
		return self.required and not self.is_satisfied

	def to_dict(self) -> dict[str, object]:
		return {
			"name": self.name,
			"kind": self.kind.value,
			"status": self.status.value,
			"required": self.required,
			"message": self.message,
			"version": self.version,
			"version_specifier": self.version_specifier,
			"details": dict(self.details),
		}


class DependencyRegistry:
	"""Register and run explicitly configured, read-only dependency checks."""

	def __init__(self) -> None:
		self._dependencies: dict[str, Dependency] = {}

	@property
	def dependencies(self) -> Mapping[str, Dependency]:
		return dict(self._dependencies)

	def register(self, dependency: Dependency) -> None:
		if dependency.name in self._dependencies:
			raise ValueError(f"Dependency already registered: {dependency.name}")
		self._dependencies[dependency.name] = dependency

	def register_many(self, dependencies: Sequence[Dependency]) -> None:
		for dependency in dependencies:
			self.register(dependency)

	def check(self, name: str) -> DependencyResult:
		dependency = self._dependencies[name]
		try:
			result = dependency.check()
			if not isinstance(result, CheckResult):
				raise TypeError("Dependency checks must return CheckResult")
		except TimeoutError as error:
			result = CheckResult(DependencyStatus.TIMED_OUT, str(error) or "Check timed out")
		except Exception as error:
			result = CheckResult(DependencyStatus.FAILED, f"Check failed: {error}")

		status = result.status
		message = result.message
		if status is DependencyStatus.SATISFIED and dependency.version_specifier is not None:
			if result.version is None:
				status = DependencyStatus.UNKNOWN
				message = "Check did not report a version required by the constraint"
			else:
				try:
					version = Version(result.version)
				except InvalidVersion:
					status = DependencyStatus.UNKNOWN
					message = f"Check returned an invalid version: {result.version}"
				else:
					if version not in SpecifierSet(dependency.version_specifier):
						status = DependencyStatus.INCOMPATIBLE
						message = (
							f"Version {version} does not satisfy "
							f"{dependency.version_specifier}"
						)

		return DependencyResult(
			name=dependency.name,
			kind=dependency.kind,
			status=status,
			required=dependency.required,
			message=message,
			version=result.version,
			version_specifier=dependency.version_specifier,
			details=result.details,
		)

	def check_all(self, names: Sequence[str] | None = None) -> dict[str, DependencyResult]:
		selected = tuple(self._dependencies) if names is None else tuple(names)
		return {name: self.check(name) for name in selected}