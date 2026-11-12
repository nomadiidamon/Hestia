"""@example software_01_dependency_checks.py

Compose read-only checks for common and platform-specific dependencies.
"""

import os
import sys
from pathlib import Path

from Hestia.software.dependency import (
	CheckResult,
	CustomDependency,
	DependencyRegistry,
	DirectoryDependency,
	DriverDependency,
	EnvironmentVariableDependency,
	FileDependency,
	PythonPackageDependency,
	ServiceDependency,
	SystemCommandDependency,
	SystemLibraryDependency,
)
from Hestia.software.dependency import DependencyStatus
from Hestia.software.doctor import Doctor


def configured_library_probe() -> CheckResult:
    """Stand in for an application-supplied, platform-specific library probe."""
    return CheckResult(
        DependencyStatus.SATISFIED,
        "Example native library is available through the application adapter",
        version="2.1.0",
    )


def configured_driver_probe(timeout_seconds: float) -> CheckResult:
    """Demonstrate the timeout contract without querying a real driver."""
    return CheckResult(
        DependencyStatus.UNKNOWN,
        f"No driver adapter configured (probe budget: {timeout_seconds:.1f}s)",
    )


def main() -> None:
    example_dir = Path(__file__).resolve().parent
    os.environ.setdefault("HESTIA_EXAMPLE_MODE", "read-only")

    registry = DependencyRegistry()
    registry.register_many([
        PythonPackageDependency("packaging", version_specifier=">=23"),
        SystemCommandDependency("python", required=False),
        FileDependency(Path(__file__), name="example-script"),
        DirectoryDependency(example_dir, name="example-directory"),
        EnvironmentVariableDependency(
            "HESTIA_EXAMPLE_MODE", expected_value="read-only", required=False
        ),
        ServiceDependency(
            "sample-service",
            lambda timeout: timeout > 0,
            required=False,
            timeout_seconds=0.5,
        ),
        SystemLibraryDependency(
            "sample-native-library",
            configured_library_probe,
            version_specifier=">=2",
            required=False,
        ),
        DriverDependency(
            "sample-device-driver",
            configured_driver_probe,
            required=False,
        ),
        CustomDependency(
            "application-policy",
            lambda: CheckResult(
                DependencyStatus.SATISFIED,
                "Application-specific policy check passed",
            ),
        ),
    ])

    report = Doctor(registry).run()
    print("Read-only dependency report")
    for name, result in report.dependencies.items():
        version = f" ({result.version})" if result.version else ""
        required = "required" if result.required else "optional"
        print(f"- {name}: {result.status.value}{version}; {required}; {result.message}")
    print(f"Failed dependencies: {list(report.failed_dependencies)}")


if __name__ == "__main__":
	main()