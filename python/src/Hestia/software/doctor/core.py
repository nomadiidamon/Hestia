"""Read-only health aggregation with repair delegated to the installer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Iterable, Mapping, Sequence

from ..dependency import DependencyRegistry, DependencyResult
from ..installer import InstallAuthorization, InstallPlan, InstallProgress, InstallReport, Installer


class DiagnosticSeverity(str, Enum):
	INFO = "info"
	WARNING = "warning"
	ERROR = "error"


@dataclass(frozen=True)
class Diagnostic:
	code: str
	message: str
	severity: DiagnosticSeverity = DiagnosticSeverity.WARNING
	dependency_name: str | None = None
	recommendation: str | None = None


DiagnosticProvider = Callable[[Mapping[str, DependencyResult]], Iterable[Diagnostic]]


@dataclass(frozen=True)
class DoctorReport:
	dependencies: Mapping[str, DependencyResult]
	diagnostics: tuple[Diagnostic, ...]

	@property
	def healthy(self) -> bool:
		return not any(result.is_blocking for result in self.dependencies.values()) and not any(
			diagnostic.severity is DiagnosticSeverity.ERROR for diagnostic in self.diagnostics
		)

	def to_dict(self) -> dict[str, object]:
		return {
			"healthy": self.healthy,
			"dependencies": {
				name: result.to_dict() for name, result in self.dependencies.items()
			},
			"diagnostics": [
				{
					"code": diagnostic.code,
					"message": diagnostic.message,
					"severity": diagnostic.severity.value,
					"dependency_name": diagnostic.dependency_name,
					"recommendation": diagnostic.recommendation,
				}
				for diagnostic in self.diagnostics
			],
		}


class Doctor:
	"""Run checks and caller-defined diagnostics without performing repairs."""

	def __init__(self, registry: DependencyRegistry) -> None:
		self.registry = registry

	def run(
		self,
		*,
		names: Sequence[str] | None = None,
		diagnostics: Iterable[Diagnostic] | DiagnosticProvider = (),
	) -> DoctorReport:
		dependencies = self.registry.check_all(names)
		if callable(diagnostics):
			try:
				collected = tuple(diagnostics(dependencies))
			except Exception as error:
				collected = (Diagnostic(
					"diagnostic_provider_failed",
					f"Diagnostic provider failed: {error}",
					DiagnosticSeverity.ERROR,
				),)
		else:
			collected = tuple(diagnostics)
		return DoctorReport(dependencies, collected)

	def repair(
		self,
		installer: Installer,
		plan: InstallPlan,
		authorization: InstallAuthorization,
		*,
		progress: Callable[[InstallProgress], None] | None = None,
	) -> InstallReport:
		return installer.execute(plan, authorization, progress=progress)