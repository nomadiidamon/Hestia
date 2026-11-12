@page python_package_readme Hestia for Python

# Hestia for Python

Hestia provides system discovery, hardware analysis, reusable software
dependency checks, and AI model recommendations. Its Python package provides
hardware profiles and reusable dependency, doctor, and installer frameworks.
These software frameworks are Python-only; C++ is not implemented.

The distribution is named `hestia-system`; import it as `Hestia`.

## Installation

```bash
python -m pip install hestia-system
```

Optional dependencies are available as extras:

```bash
python -m pip install "hestia-system[nvidia]"  # NVIDIA telemetry support
python -m pip install "hestia-system[dev]"     # pytest
```

## Usage

```python
from Hestia import AcceleratorType, ModelSize, get_model_info
import Hestia

info = get_model_info(AcceleratorType.NVIDIA_CUDA, ModelSize.SMALL)
print(info)

profile = Hestia.detect_hardware()
recommendation = Hestia.recommend_model(profile)
Hestia.print_hardware_report(profile, recommendation)
```

Currently only caller-registered dependencies are checked; whole-system
software analysis is planned for the next implementation phase, which will add
a software catalog. Built-in checks cover Python packages,
commands, files, directories, and environment variables. Callers can supply
probes for services, system libraries, drivers, and custom requirements.
Checks and doctor reports are read-only. A command version query runs only
when configured by the caller and is bounded by a timeout.

Software dependencies can be checked and summarized independently:

```python
from Hestia.software.dependency import DependencyRegistry, SystemCommandDependency
from Hestia.software.doctor import Doctor

registry = DependencyRegistry()
registry.register(SystemCommandDependency("git"))
report = Doctor(registry).run()
print(report.to_dict())
print(report.failed_dependencies)
```

`failed_dependencies` is an ordered list callers can display to end users or
use to choose which caller-defined repairs to offer.

Installation is performed only through caller-supplied requests and injected
backends, with authorization scoped to the approved dependency group and
actions. The installer skips already-satisfied dependencies, reports
unsupported backends and failures, and rechecks affected dependencies.
Authorization is an application-level scope check, not a security credential
or sandbox. Hestia does not prompt for approval, infer what to install, choose
packages or package managers, escalate privileges, or perform repairs during
checks or doctor reports. The doctor aggregates dependency results and
caller-defined diagnostics; repairs must be explicitly delegated to the
installer.

To track installations, create an `InstallProgressTracker` from
`Hestia.software.installer` and pass it as `progress=tracker` to
`Installer.execute()` or `Doctor.repair()`. `tracker.actions` is a thread-safe
snapshot keyed by action ID; each event has a `completed` fraction from 0 to 1
or `None` when unknown, plus a terminal `status` when the action finishes.
Run the synchronous installation on a worker thread to inspect it while it
runs. Intermediate fractions come from the backend and are only as accurate as
its measurements. A successful action reaches 1.0 before dependency rechecks;
inspect the returned report for overall success. Invalid fractions are ignored
and reported in `progress_errors`.

The package supports Python versions declared by the project metadata (Python
3.10 and later).

## Development

From the repository checkout:

```bash
cd python
python -m pip install -e ".[dev]"
python -m pytest
```

Package metadata is maintained in the repository's `project.ini`. Source
distributions include a copy of that file so they can be built independently
of the repository checkout.
