"""@example software_07_install_progress.py

Simulate a 15-second installation with real-time progress; no software is installed.
"""

import time

from Auctor.Stylus.TTY import TTY
from Hestia.software.dependency import CheckResult, CustomDependency, DependencyRegistry, DependencyStatus
from Hestia.software.installer import (
    InstallAuthorization, InstallOutcome, InstallProgressTracker, InstallRequest, Installer,
)


class SimulatedBackend:
    def __init__(self) -> None:
        self.installed = False

    def install(self, request, *, timeout_seconds, report_progress):
        for second in range(1, 16):
            time.sleep(1)
            report_progress("Simulating installation", second / 15)
        self.installed = True
        return InstallOutcome(True, f"Simulated installation of {request.target}")


def main() -> None:
    backend = SimulatedBackend()
    registry = DependencyRegistry()
    registry.register(CustomDependency(
        "example-runtime",
        lambda: CheckResult(
            DependencyStatus.SATISFIED if backend.installed else DependencyStatus.MISSING,
            "Installed in memory" if backend.installed else "Not installed",
        ),
    ))
    request = InstallRequest("install-runtime", "example", "example-runtime", "simulation", "demo-runtime")
    installer = Installer(registry, {"simulation": backend}, timeout_seconds=30)
    plan = installer.plan([request], registry.check_all())
    authorization = InstallAuthorization("example", frozenset({request.action_id}))
    terminal = TTY().is_tty()
    tracker = InstallProgressTracker(display=terminal)

    def progress(event):
        tracker(event)
        if not terminal:
            percent = f" ({event.completed:.1%})" if event.completed is not None else ""
            print(f"{event.dependency_name}: {event.message}{percent}", flush=True)

    print("Simulating installation for 15 seconds; no software will be installed.", flush=True)
    report = installer.execute(plan, authorization, progress=progress)
    print(f"Installation result: {'succeeded' if report.succeeded else 'failed'}")


if __name__ == "__main__":
    main()