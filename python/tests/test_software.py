import subprocess
from threading import Event, Thread

import pytest

from Hestia.software.dependency import (
	CheckResult,
	CommandCheck,
	CustomDependency,
	Dependency,
	DependencyKind,
	DependencyRegistry,
	DependencySpec,
	DependencyStatus,
	DirectoryDependency,
	DriverDependency,
	EnvironmentVariableCheck,
	EnvironmentVariableDependency,
	FileDependency,
	PathCheck,
	PythonPackageDependency,
	PythonPackageCheck,
	ServiceCheck,
	ServiceDependency,
	SystemCommandDependency,
	SystemLibraryDependency,
	parse_first_version,
)
from Hestia.software.dependency import checks as checks_module
from Hestia.software.doctor import Diagnostic, DiagnosticSeverity, Doctor
from Hestia.software.installer import (
	InstallActionStatus,
	InstallAuthorization,
	InstallOutcome,
	InstallProgressTracker,
	InstallRequest,
	Installer,
)


def test_registry_checks_requirements_and_version_constraints():
	registry = DependencyRegistry()
	registry.register_many([
		DependencySpec(
			"engine",
			lambda: CheckResult(DependencyStatus.SATISFIED, "Found", version="2.4.1"),
			kind=DependencyKind.CUSTOM,
			version_specifier=">=2,<3",
		),
		DependencySpec(
			"optional",
			lambda: CheckResult(DependencyStatus.MISSING, "Not installed"),
			required=False,
		),
	])

	results = registry.check_all()
	assert results["engine"].is_satisfied
	assert not results["optional"].is_blocking
	assert results["optional"].to_dict()["status"] == "missing"


def test_registry_reports_incompatible_version_unknown_version_and_duplicate():
	registry = DependencyRegistry()
	registry.register(DependencySpec(
		"tool",
		lambda: CheckResult(DependencyStatus.SATISFIED, "Found", version="1.2"),
		version_specifier=">=2",
	))
	assert registry.check("tool").status is DependencyStatus.INCOMPATIBLE

	registry.register(DependencySpec(
		"versionless",
		lambda: CheckResult(DependencyStatus.SATISFIED, "Found"),
		version_specifier=">=1",
	))
	assert registry.check("versionless").status is DependencyStatus.UNKNOWN
	with pytest.raises(ValueError, match="already registered"):
		registry.register(DependencySpec("tool", lambda: CheckResult(DependencyStatus.MISSING, "")))
	with pytest.raises(ValueError, match="Invalid version specifier"):
		DependencySpec("bad", lambda: CheckResult(DependencyStatus.MISSING, ""), version_specifier="wat")


@pytest.mark.parametrize(
	("check", "expected"),
	[
		(lambda: (_ for _ in ()).throw(TimeoutError("slow")), DependencyStatus.TIMED_OUT),
		(lambda: (_ for _ in ()).throw(RuntimeError("broken")), DependencyStatus.FAILED),
	])
def test_registry_converts_check_exceptions_to_results(check, expected):
	registry = DependencyRegistry()
	registry.register(DependencySpec("custom", check))
	assert registry.check("custom").status is expected


def test_python_package_check_uses_distribution_metadata(monkeypatch):
	monkeypatch.setattr(checks_module.importlib.metadata, "version", lambda _: "3.2.1")
	result = PythonPackageCheck("example")( )
	assert result.status is DependencyStatus.SATISFIED
	assert result.version == "3.2.1"

	def missing(_):
		raise checks_module.importlib.metadata.PackageNotFoundError

	monkeypatch.setattr(checks_module.importlib.metadata, "version", missing)
	assert PythonPackageCheck("example")().status is DependencyStatus.MISSING


def test_command_check_is_configured_and_bounded(monkeypatch):
	monkeypatch.setattr(checks_module.shutil, "which", lambda _: "C:/tools/app.exe")
	seen = {}

	def run(args, **kwargs):
		seen["args"] = args
		seen.update(kwargs)
		return subprocess.CompletedProcess(args, 0, stdout="app 1.4.0", stderr="")

	monkeypatch.setattr(checks_module.subprocess, "run", run)
	check = CommandCheck(
		"app",
		version_args=("--version",),
		version_parser=parse_first_version,
		timeout_seconds=2,
	)
	result = check()
	assert result.version == "1.4.0"
	assert seen["args"] == ["C:/tools/app.exe", "--version"]
	assert seen["timeout"] == 2

	monkeypatch.setattr(
		checks_module.subprocess,
		"run",
		lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired(args[0], 1)),
	)
	assert check().status is DependencyStatus.TIMED_OUT


def test_path_environment_and_caller_supplied_service_checks(tmp_path, monkeypatch):
	file_path = tmp_path / "config.ini"
	file_path.write_text("value", encoding="utf-8")
	assert PathCheck(file_path, directory=False)().status is DependencyStatus.SATISFIED
	assert PathCheck(tmp_path, directory=True)().status is DependencyStatus.SATISFIED

	monkeypatch.setenv("HESTIA_TEST_SETTING", "ready")
	assert EnvironmentVariableCheck(
		"HESTIA_TEST_SETTING", expected_value="ready"
	)().status is DependencyStatus.SATISFIED
	assert EnvironmentVariableCheck(
		"HESTIA_TEST_SETTING", expected_value="other"
	)().status is DependencyStatus.INCOMPATIBLE

	seen = []
	service = ServiceCheck(lambda timeout: seen.append(timeout) or True, timeout_seconds=1.5)
	assert service().status is DependencyStatus.SATISFIED
	assert seen == [1.5]


def test_first_version_parser():
	assert parse_first_version("tool version v2.3.4") == "2.3.4"
	assert parse_first_version("no version reported") is None


def test_dependency_types_cover_each_kind(tmp_path):
	check = lambda: CheckResult(DependencyStatus.SATISFIED, "Available")
	dependencies = [
		PythonPackageDependency("sample"),
		SystemCommandDependency("sample"),
		SystemLibraryDependency("sample-library", check),
		DriverDependency("sample-driver", check),
		FileDependency(tmp_path / "sample.file"),
		DirectoryDependency(tmp_path),
		EnvironmentVariableDependency("SAMPLE"),
		ServiceDependency("sample-service", lambda _: True),
		CustomDependency("sample-custom", check),
	]

	assert all(isinstance(dependency, Dependency) for dependency in dependencies)
	assert [dependency.kind for dependency in dependencies] == [
		DependencyKind.PYTHON_PACKAGE,
		DependencyKind.SYSTEM_COMMAND,
		DependencyKind.SYSTEM_LIBRARY,
		DependencyKind.DRIVER,
		DependencyKind.FILE,
		DependencyKind.DIRECTORY,
		DependencyKind.ENVIRONMENT_VARIABLE,
		DependencyKind.SERVICE,
		DependencyKind.CUSTOM,
	]
	assert DependencySpec is Dependency


class FakeBackend:
	def __init__(self, *, succeeds=True, on_success=None, outcome_succeeds=True):
		self.succeeds = succeeds
		self.on_success = on_success
		self.outcome_succeeds = outcome_succeeds
		self.calls = []

	def install(self, request, *, timeout_seconds, report_progress):
		self.calls.append((request, timeout_seconds))
		report_progress("Fetching", 0.5)
		if not self.succeeds:
			raise TimeoutError
		if self.on_success is not None:
			self.on_success()
		return InstallOutcome(
			self.outcome_succeeds,
			"Installed" if self.outcome_succeeds else "Installation rejected",
			{"target": request.target},
		)


def make_install_setup(backend=None):
	state = {"ready": False}
	if backend is not None:
		backend.on_success = lambda: state.__setitem__("ready", True)
	registry = DependencyRegistry()
	registry.register(CustomDependency(
		"engine",
		lambda: CheckResult(
			DependencyStatus.SATISFIED if state["ready"] else DependencyStatus.MISSING,
			"Installed" if state["ready"] else "Missing",
		),
	))
	installer = Installer(registry, {"test": backend} if backend is not None else {})
	request = InstallRequest(
		"install-engine", "runtime", "engine", "test", "engine-package", source="https://example.invalid/engine"
	)
	plan = installer.plan([request], registry.check_all())
	return registry, installer, plan, state


def test_installer_requires_scoped_authorization_and_rechecks_with_progress():
	backend = FakeBackend()
	registry, installer, plan, _ = make_install_setup(backend)
	with pytest.raises(PermissionError, match="does not cover"):
		installer.execute(plan, InstallAuthorization("runtime", frozenset()))
	assert backend.calls == []

	events = []
	report = installer.execute(
		plan,
		InstallAuthorization("runtime", frozenset({"install-engine"})),
		progress=events.append,
	)
	assert report.actions[0].status is InstallActionStatus.SUCCEEDED
	assert report.rechecks["engine"].is_satisfied
	assert report.failed_dependencies == []
	assert [event.message for event in events] == ["Installation started", "Fetching", "Installation finished"]
	assert backend.calls[0][1] == 300


def test_install_progress_tracker_records_events_during_execution():
	tracker = InstallProgressTracker()
	backend = FakeBackend()
	registry, installer, plan, _ = make_install_setup(backend)
	backend.on_success = lambda: (
		tracker.actions["install-engine"].completed == 0.5
		or pytest.fail("Backend progress was not recorded")
	)
	installer.execute(plan, InstallAuthorization("runtime", frozenset({"install-engine"})), progress=tracker)
	assert tracker.actions["install-engine"].completed == 1.0
	assert tracker.actions["install-engine"].message == "Installation finished"
	assert tracker.actions["install-engine"].status is InstallActionStatus.SUCCEEDED


def test_install_progress_tracker_can_be_read_while_backend_runs():
	started = Event()
	resume = Event()
	tracker = InstallProgressTracker()

	class BlockingBackend:
		def install(self, request, *, timeout_seconds, report_progress):
			report_progress("Downloading", 0.4)
			started.set()
			if not resume.wait(5):
				raise TimeoutError("Test backend was not released")
			return InstallOutcome(True, "Done")

	registry, installer, plan, _ = make_install_setup()
	installer.backends["test"] = BlockingBackend()
	worker = Thread(target=installer.execute, args=(
		plan, InstallAuthorization("runtime", frozenset({"install-engine"})),
	), kwargs={"progress": tracker})
	worker.start()
	try:
		assert started.wait(5)
		assert tracker.actions["install-engine"].completed == 0.4
		assert tracker.actions["install-engine"].status is None
	finally:
		resume.set()
		worker.join(5)
	assert not worker.is_alive()
	assert tracker.actions["install-engine"].status is InstallActionStatus.SUCCEEDED


@pytest.mark.parametrize("backend, expected", [
	(None, InstallActionStatus.UNSUPPORTED),
	(FakeBackend(succeeds=False), InstallActionStatus.TIMED_OUT),
	(FakeBackend(outcome_succeeds=False), InstallActionStatus.FAILED),
])
def test_install_progress_tracker_reports_terminal_failures(backend, expected):
	tracker = InstallProgressTracker()
	registry, installer, plan, _ = make_install_setup(backend)
	installer.execute(plan, InstallAuthorization("runtime", frozenset({"install-engine"})), progress=tracker)
	event = tracker.actions["install-engine"]
	assert event.status is expected
	assert event.completed is None


def test_install_progress_tracker_reports_backend_exception():
	class FailingBackend:
		def install(self, request, *, timeout_seconds, report_progress):
			raise RuntimeError("Backend unavailable")

	registry, installer, plan, _ = make_install_setup()
	installer.backends["test"] = FailingBackend()
	tracker = InstallProgressTracker()
	installer.execute(plan, InstallAuthorization("runtime", frozenset({"install-engine"})), progress=tracker)
	assert tracker.actions["install-engine"].status is InstallActionStatus.FAILED
	assert "Backend unavailable" in tracker.actions["install-engine"].message


def test_installer_discards_invalid_progress_fractions():
	class InvalidProgressBackend:
		def install(self, request, *, timeout_seconds, report_progress):
			for completed in (-0.1, 1.1, float("nan"), float("inf"), True, 10**400):
				report_progress("Invalid", completed)
			return InstallOutcome(True, "Done")

	registry, installer, plan, _ = make_install_setup()
	installer.backends["test"] = InvalidProgressBackend()
	events = []
	report = installer.execute(
		plan, InstallAuthorization("runtime", frozenset({"install-engine"})), progress=events.append,
	)
	assert [event.completed for event in events] == [0.0, 1.0]
	assert len(report.progress_errors) == 6


def test_install_report_is_not_successful_when_recheck_fails():
	backend = FakeBackend()
	registry, installer, plan, _ = make_install_setup(backend)
	backend.on_success = lambda: None
	report = installer.execute(
		plan, InstallAuthorization("runtime", frozenset({"install-engine"}))
	)
	assert report.actions[0].status is InstallActionStatus.SUCCEEDED
	assert report.rechecks["engine"].status is DependencyStatus.MISSING
	assert not report.succeeded
	assert report.failed_dependencies == ["engine"]
	assert report.to_dict()["failed_dependencies"] == ["engine"]


def test_install_report_lists_failed_action_when_recheck_succeeds():
	backend = FakeBackend(outcome_succeeds=False)
	registry, installer, plan, _ = make_install_setup(backend)
	report = installer.execute(
		plan, InstallAuthorization("runtime", frozenset({"install-engine"}))
	)
	assert report.actions[0].status is InstallActionStatus.FAILED
	assert report.rechecks["engine"].is_satisfied
	assert report.failed_dependencies == ["engine"]


def test_installer_skips_satisfied_and_reports_unsupported_or_timeout():
	registry, installer, plan, _ = make_install_setup()
	unsupported = installer.execute(
		plan,
		InstallAuthorization("runtime", frozenset({"install-engine"})),
	)
	assert unsupported.actions[0].status is InstallActionStatus.UNSUPPORTED
	assert unsupported.rechecks["engine"].status is DependencyStatus.MISSING
	assert unsupported.failed_dependencies == ["engine"]

	backend = FakeBackend(succeeds=False)
	registry, installer, plan, state = make_install_setup(backend)
	timed_out = installer.execute(
		plan, InstallAuthorization("runtime", frozenset({"install-engine"}))
	)
	assert timed_out.actions[0].status is InstallActionStatus.TIMED_OUT
	assert timed_out.failed_dependencies == ["engine"]

	request = InstallRequest("again", "runtime", "engine", "test", "engine-package")
	state["ready"] = True
	satisfied = installer.plan([request], {
		"engine": registry.check("engine"),
	})
	assert satisfied.actions == ()
	assert satisfied.skipped_dependencies == ("engine",)


def test_doctor_aggregates_diagnostics_and_delegates_repair():
	backend = FakeBackend()
	registry, installer, plan, _ = make_install_setup(backend)
	doctor = Doctor(registry)
	report = doctor.run(diagnostics=lambda dependencies: [
		Diagnostic(
			"engine_missing",
			"Engine is unavailable",
			DiagnosticSeverity.ERROR,
			dependency_name="engine",
			recommendation="Install the approved engine package",
		)
	])
	assert not report.healthy
	assert report.dependencies["engine"].status is DependencyStatus.MISSING
	assert report.failed_dependencies == ["engine"]
	assert report.to_dict()["failed_dependencies"] == ["engine"]
	assert report.to_dict()["diagnostics"][0]["code"] == "engine_missing"

	tracker = InstallProgressTracker()
	installation = doctor.repair(
		installer,
		plan,
		InstallAuthorization("runtime", frozenset({"install-engine"})),
		progress=tracker,
	)
	assert installation.actions[0].status is InstallActionStatus.SUCCEEDED
	assert installation.failed_dependencies == []
	assert tracker.actions["install-engine"].status is InstallActionStatus.SUCCEEDED


def test_doctor_lists_optional_failures_without_marking_report_unhealthy():
	registry = DependencyRegistry()
	registry.register_many([
		CustomDependency("first", lambda: CheckResult(DependencyStatus.MISSING, "Missing"), required=False),
		CustomDependency("second", lambda: CheckResult(DependencyStatus.UNKNOWN, "Unknown"), required=False),
	])
	report = Doctor(registry).run()
	assert report.healthy
	assert report.failed_dependencies == ["first", "second"]
	assert report.to_dict()["failed_dependencies"] == ["first", "second"]


def test_installer_lists_failed_dependencies_once_in_action_order():
	registry = DependencyRegistry()
	registry.register_many([
		CustomDependency("first", lambda: CheckResult(DependencyStatus.MISSING, "Missing")),
		CustomDependency("second", lambda: CheckResult(DependencyStatus.MISSING, "Missing")),
	])
	installer = Installer(registry, {})
	requests = [
		InstallRequest("one", "group", "second", "missing", "target"),
		InstallRequest("two", "group", "first", "missing", "target"),
		InstallRequest("three", "group", "second", "missing", "target"),
	]
	plan = installer.plan(requests, registry.check_all())
	report = installer.execute(plan, InstallAuthorization("group", frozenset({"one", "two", "three"})))
	assert not report.succeeded
	assert report.failed_dependencies == ["second", "first"]
	assert report.to_dict()["failed_dependencies"] == ["second", "first"]