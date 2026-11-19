import subprocess

import pytest

from Hestia.software.dependency import (
    CheckResult, CommandCheck, CustomDependency, Dependency, DependencyKind,
    DependencyRegistry, DependencySpec, DependencyStatus, DirectoryDependency,
    DriverDependency, EnvironmentVariableCheck, EnvironmentVariableDependency,
    FileDependency, PathCheck, PythonPackageDependency, PythonPackageCheck,
    ServiceCheck, ServiceDependency, SystemCommandDependency,
    SystemLibraryDependency, parse_first_version,
)
from Hestia.software.dependency import checks as checks_module


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
