"""@example software_03_doctor.py

Aggregate checks and diagnostics, then delegate approved repair to installer.
"""

from Hestia.software.dependency import CheckResult, CustomDependency, DependencyRegistry
from Hestia.software.dependency import DependencyStatus
from Hestia.software.doctor import Diagnostic, DiagnosticSeverity, Doctor
from Hestia.software.installer import (
	InstallAuthorization,
	InstallOutcome,
    InstallProgressTracker,
	InstallRequest,
	Installer,
)


class InMemoryRuntimeBackend:
    def __init__(self) -> None:
        self.runtime_available = False

    def install(self, request, *, timeout_seconds, report_progress):
        report_progress("Preparing simulated runtime", 0.4)
        self.runtime_available = True
        report_progress("Simulated runtime is ready", 1.0)
        return InstallOutcome(True, "Example runtime enabled in memory")


def main() -> None:
    backend = InMemoryRuntimeBackend()
    registry = DependencyRegistry()
    registry.register(CustomDependency(
        "example-runtime",
        lambda: CheckResult(
            DependencyStatus.SATISFIED if backend.runtime_available else DependencyStatus.MISSING,
            "Runtime is available" if backend.runtime_available else "Runtime is not configured",
        ),
    ))
    doctor = Doctor(registry)

    def runtime_diagnostics(dependencies):
        if dependencies["example-runtime"].is_satisfied:
            return ()
        return (Diagnostic(
            code="runtime_unavailable",
            message="The application runtime is not available.",
            severity=DiagnosticSeverity.ERROR,
            dependency_name="example-runtime",
            recommendation="Review the application-provided runtime installation request.",
        ),)

    before = doctor.run(diagnostics=runtime_diagnostics)
    print("Initial doctor report:")
    print(before.to_dict())
    print(f"Failed dependencies: {list(before.failed_dependencies)}")

    # This action and target come from the application, not from Doctor.
    request = InstallRequest(
        action_id="configure-example-runtime",
        group_id="example-application",
        dependency_name="example-runtime",
        backend="memory",
        target="demo-runtime",
        instructions="This example updates only in-memory state.",
    )
    installer = Installer(registry, {"memory": backend}, timeout_seconds=10)
    plan = installer.plan([request], before.dependencies)

    # A real application supplies this scope only after external approval.
    authorization = InstallAuthorization(
        group_id="example-application",
        action_ids={"configure-example-runtime"},
    )
    tracker = InstallProgressTracker()
    repair = doctor.repair(installer, plan, authorization, progress=tracker)
    print("Delegated repair report:")
    print(repair.to_dict())
    print(f"Latest repair progress: {tracker.actions}")
    print(f"Failed dependencies: {list(repair.failed_dependencies)}")

    after = doctor.run(diagnostics=runtime_diagnostics)
    print("Doctor report after recheck:")
    print(after.to_dict())
    print(f"Failed dependencies: {list(after.failed_dependencies)}")
    print(f"Application healthy: {after.healthy}")


if __name__ == "__main__":
	main()