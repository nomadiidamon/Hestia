"""Caller-directed installation planning and backend execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Mapping, Protocol, Sequence

from ..dependency import DependencyRegistry, DependencyResult


@dataclass(frozen=True)
class InstallRequest:
	action_id: str
	group_id: str
	dependency_name: str
	backend: str
	target: str
	source: str | None = None
	instructions: str | None = None
	options: Mapping[str, str] = field(default_factory=dict)

	def __post_init__(self) -> None:
		for field_name in ("action_id", "group_id", "dependency_name", "backend", "target"):
			if not getattr(self, field_name).strip():
				raise ValueError(f"{field_name} must not be empty")


@dataclass(frozen=True)
class InstallAuthorization:
	"""Caller-provided approval scope; this is not a security credential."""

	group_id: str
	action_ids: frozenset[str]

	def __post_init__(self) -> None:
		object.__setattr__(self, "action_ids", frozenset(self.action_ids))


@dataclass(frozen=True)
class InstallPlan:
	group_id: str
	actions: tuple[InstallRequest, ...]
	skipped_dependencies: tuple[str, ...] = ()


class InstallActionStatus(str, Enum):
	SUCCEEDED = "succeeded"
	FAILED = "failed"
	TIMED_OUT = "timed_out"
	UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class InstallOutcome:
	succeeded: bool
	message: str
	details: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class InstallProgress:
	action_id: str
	dependency_name: str
	message: str
	completed: float | None = None


class InstallationBackend(Protocol):
	def install(
		self,
		request: InstallRequest,
		*,
		timeout_seconds: float,
		report_progress: Callable[[str, float | None], None],
	) -> InstallOutcome: ...


@dataclass(frozen=True)
class InstallActionResult:
	action_id: str
	dependency_name: str
	status: InstallActionStatus
	message: str
	details: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class InstallReport:
	group_id: str
	actions: tuple[InstallActionResult, ...]
	rechecks: Mapping[str, DependencyResult]
	progress_errors: tuple[str, ...] = ()

	@property
	def failed_dependencies(self) -> list[str]:
		failed_actions = (
			action.dependency_name
			for action in self.actions
			if action.status is not InstallActionStatus.SUCCEEDED
		)
		failed_rechecks = (
			name for name, result in self.rechecks.items() if not result.is_satisfied
		)
		return list(dict.fromkeys((*failed_actions, *failed_rechecks)))

	@property
	def succeeded(self) -> bool:
		return (
			all(action.status is InstallActionStatus.SUCCEEDED for action in self.actions)
			and all(result.is_satisfied for result in self.rechecks.values())
		)

	def to_dict(self) -> dict[str, object]:
		return {
			"group_id": self.group_id,
			"succeeded": self.succeeded,
			"failed_dependencies": self.failed_dependencies,
			"actions": [
				{
					"action_id": action.action_id,
					"dependency_name": action.dependency_name,
					"status": action.status.value,
					"message": action.message,
					"details": dict(action.details),
				}
				for action in self.actions
			],
			"rechecks": {name: result.to_dict() for name, result in self.rechecks.items()},
			"progress_errors": list(self.progress_errors),
		}


class Installer:
	"""Plan caller-supplied actions and run only within caller approval scope."""

	def __init__(
		self,
		registry: DependencyRegistry,
		backends: Mapping[str, InstallationBackend],
		*,
		timeout_seconds: float = 300.0,
	) -> None:
		if timeout_seconds <= 0:
			raise ValueError("timeout_seconds must be positive")
		self.registry = registry
		self.backends = dict(backends)
		self.timeout_seconds = timeout_seconds

	def plan(
		self,
		requests: Sequence[InstallRequest],
		check_results: Mapping[str, DependencyResult],
	) -> InstallPlan:
		groups = {request.group_id for request in requests}
		if len(groups) > 1:
			raise ValueError("An install plan must contain one dependency group")
		group_id = next(iter(groups), "")
		seen_actions: set[str] = set()
		planned: list[InstallRequest] = []
		skipped: list[str] = []
		for request in requests:
			if request.action_id in seen_actions:
				raise ValueError(f"Duplicate install action: {request.action_id}")
			seen_actions.add(request.action_id)
			if request.dependency_name not in self.registry.dependencies:
				raise ValueError(f"Dependency is not registered: {request.dependency_name}")
			if request.dependency_name not in check_results:
				raise ValueError(f"Missing check result: {request.dependency_name}")
			if check_results[request.dependency_name].is_satisfied:
				skipped.append(request.dependency_name)
			else:
				planned.append(request)
		return InstallPlan(group_id, tuple(planned), tuple(skipped))

	def execute(
		self,
		plan: InstallPlan,
		authorization: InstallAuthorization,
		*,
		progress: Callable[[InstallProgress], None] | None = None,
	) -> InstallReport:
		if authorization.group_id != plan.group_id:
			raise PermissionError("Authorization does not match the install group")
		unauthorized = {action.action_id for action in plan.actions} - authorization.action_ids
		if unauthorized:
			raise PermissionError(
				"Authorization does not cover install actions: " + ", ".join(sorted(unauthorized))
			)
		if any(action.group_id != plan.group_id for action in plan.actions):
			raise ValueError("Install action group does not match the plan")
		if len({action.action_id for action in plan.actions}) != len(plan.actions):
			raise ValueError("Install plan contains duplicate action identifiers")
		registered = self.registry.dependencies
		if any(action.dependency_name not in registered for action in plan.actions):
			raise ValueError("Install plan contains an unregistered dependency")

		results: list[InstallActionResult] = []
		progress_errors: list[str] = []
		for request in plan.actions:
			backend = self.backends.get(request.backend)
			if backend is None:
				results.append(InstallActionResult(
					request.action_id,
					request.dependency_name,
					InstallActionStatus.UNSUPPORTED,
					request.instructions or f"No installation backend: {request.backend}",
				))
				continue

			def report_progress(message: str, completed: float | None = None) -> None:
				if progress is None:
					return
				try:
					progress(InstallProgress(
						request.action_id, request.dependency_name, message, completed
					))
				except Exception as error:
					progress_errors.append(f"{request.action_id}: {error}")

			report_progress("Installation started", 0.0)
			try:
				outcome = backend.install(
					request,
					timeout_seconds=self.timeout_seconds,
					report_progress=report_progress,
				)
				if not isinstance(outcome, InstallOutcome):
					raise TypeError("Installation backends must return InstallOutcome")
			except TimeoutError:
				results.append(InstallActionResult(
					request.action_id,
					request.dependency_name,
					InstallActionStatus.TIMED_OUT,
					"Installation backend timed out",
				))
				continue
			except Exception as error:
				results.append(InstallActionResult(
					request.action_id,
					request.dependency_name,
					InstallActionStatus.FAILED,
					f"Installation backend failed: {error}",
				))
				continue

			status = InstallActionStatus.SUCCEEDED if outcome.succeeded else InstallActionStatus.FAILED
			results.append(InstallActionResult(
				request.action_id,
				request.dependency_name,
				status,
				outcome.message,
				outcome.details,
			))
			report_progress("Installation finished", 1.0 if outcome.succeeded else None)

		recheck_names = tuple(dict.fromkeys(action.dependency_name for action in plan.actions))
		rechecks = self.registry.check_all(recheck_names) if recheck_names else {}
		return InstallReport(plan.group_id, tuple(results), rechecks, tuple(progress_errors))