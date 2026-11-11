"""@example software_02_installer.py

Plan and execute caller-authorized installation through an in-memory backend.
"""

from Hestia.software.dependency import CheckResult, CustomDependency, DependencyRegistry
from Hestia.software.dependency import DependencyStatus
from Hestia.software.installer import (
	InstallAuthorization,
	InstallOutcome,
	InstallRequest,
	Installer,
)


class ExampleMemoryBackend:
    """Simulate installation without modifying the host environment."""

    def __init__(self) -> None:
        self.installed_targets: set[str] = set()

    def install(self, request, *, timeout_seconds, report_progress):
        report_progress("Validating the supplied target", 0.25)
        self.installed_targets.add(request.target)
        report_progress("Updated in-memory example state", 0.75)
        return InstallOutcome(
            True,
            f"Simulated installation of {request.target}",
            {"timeout_seconds": str(timeout_seconds)},
        )


def main() -> None:
    backend = ExampleMemoryBackend()
    registry = DependencyRegistry()
    registry.register(CustomDependency(
        "example-engine",
        lambda: CheckResult(
            DependencyStatus.SATISFIED
            if "example-engine-2" in backend.installed_targets
            else DependencyStatus.MISSING,
            "Installed in memory" if "example-engine-2" in backend.installed_targets else "Not installed",
        ),
    ))

    request = InstallRequest(
        action_id="install-example-engine",
        group_id="example-runtime",
        dependency_name="example-engine",
        backend="memory",
        target="example-engine-2",
        source="application-supplied example catalog",
        options={"channel": "stable"},
    )
    installer = Installer(registry, {"memory": backend}, timeout_seconds=10)
    plan = installer.plan([request], registry.check_all())

    print(f"Planned actions: {[action.action_id for action in plan.actions]}")
    print("Authorization is supplied by the caller after its own approval step.")

    try:
        installer.execute(plan, InstallAuthorization("example-runtime", frozenset()))
    except PermissionError as error:
        print(f"Unapproved execution rejected: {error}")

    def show_progress(event) -> None:
        percent = "" if event.completed is None else f" ({event.completed:.0%})"
        print(f"Progress [{event.action_id}]: {event.message}{percent}")

    authorization = InstallAuthorization(
        group_id="example-runtime",
        action_ids={"install-example-engine"},
    )
    report = installer.execute(plan, authorization, progress=show_progress)
    print("Installation report:")
    print(report.to_dict())
    print(f"Post-install check succeeded: {report.succeeded}")


if __name__ == "__main__":
	main()