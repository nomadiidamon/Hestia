@page python_implementation Python Implementation

# Python Implementation

Hestia provides system discovery, hardware analysis, reusable software
dependency checks, and AI model recommendations. This page documents the
active Python implementation.

Build, dev, and contributor notes specific to the Python side of this
project. For concepts and behavior guarantees, see
[Concepts](https://nomadiidamon.github.io/Hestia/Concepts.html) and [Semantics](https://nomadiidamon.github.io/Hestia/Semantics.html).
For why the repo is laid out this way, see [Architecture](https://nomadiidamon.github.io/Hestia/Architecture.html).

Distribution name: `hestia-system`. Import name: `Hestia`.

## Status

Implemented: `Hestia.types`, the `Hestia.models` catalog and metadata API,
`Hestia.hardware` detection/profile APIs, and top-level model recommendations.
The `Hestia.software.dependency`, `Hestia.software.installer`, and
`Hestia.software.doctor` frameworks and configured CLI inventory are implemented.
The standalone `hestia` CLI and installed console-script entry point are also
implemented. An exhaustive installed-software inventory and software-informed
model recommendations are not implemented. The legacy
`Hestia.model_catalog` path remains available.

### Command-line interface

Install the package to use the `hestia` command:

```bash
python -m pip install hestia-system
hestia report
hestia scan --json
```

Supported commands are `scan`, `hardware`, `software`, `models`, `recommend`,
and `report`. They print readable text by default; each accepts `--json`.
`hardware` and `software` serialize their respective profiles, `models`
returns a list of catalog entries, and `recommend` returns the recommendation.
`report` combines hardware and recommendation; `scan` combines hardware and
configured software. `software` and `scan` run the configured version probes
by default. Use `--no-version-probes` to avoid executing those discovered
programs. Text reports group model names by category and display each GPU or
software tool as a separate record. Use `hestia --help` for command-specific
options.

The CLI is a presentation layer over the public Python API. It does not
implement hardware detection, software version parsing, or recommendation
logic. See the [package guide](../../python/README.md#command-line-interface)
for details and the [CLI examples](../../examples/README.md#cli-examples).

### Software tooling

The software frameworks check only caller-registered requirements. Built-in
checks cover Python distributions, commands, files, directories, and
environment variables; service, system-library, driver, and custom checks use
caller-provided probes. Checks and doctor reports are read-only. Installation
requires caller-defined requests, injected backends, and authorization scoped
to the plan's group and actions. Hestia does not choose packages or package
managers, escalate privileges, or automatically repair the environment. The
authorization scope is not a security credential or sandbox.
Doctor reports list every unsatisfied dependency in `failed_dependencies`;
installer reports include failed actions and unsatisfied rechecks in the same
field. The serialized `to_dict()` output uses a list, suitable for displaying
to end users or using to select possible repairs.

## Layout

```
python/
+-- pyproject.toml     # Static packaging configuration
+-- setup.py           # Reads metadata from ../project.ini
+-- src/Hestia/        # Package source
|   +-- cli.py         # `hestia` console-script command layer
|   +-- types.py
|   +-- model_catalog.py   # Legacy path
|   +-- models/
|   +-- hardware/
|   +-- software/          # CLI inventory, dependency, installer, and doctor
|   `-- recommender.py
+-- tests/             # pytest suite
+-- scripts/           # clean / run_tests wrappers (.bat and .sh)
`-- tools/             # clean.py, run_tests.py and per-sub-package tools
    `-- models/
```

## Requirements

- Python version satisfying `project.ini`'s `[compatibility] python_requires`
  (currently 3.10 or later).
- Runtime dependencies: `psutil`, `packaging`.
- Optional extras: `nvidia` (`nvidia-ml-py`), `dev` (`pytest`).

## Setting Up a Dev Environment

```bash
cd python
python -m venv .venv
```

### Windows: Command Prompt

```bat
.venv\Scripts\activate
```

### macOS and Linux

```bash
source .venv/bin/activate
```

### Install development dependencies

```bash
pip install -e ".[dev]"
```

The build reads `../project.ini`, so install from a full repository checkout.

## Usage

### Model information

```python
import Hestia
from Hestia import AcceleratorType, ModelSize

info = Hestia.get_model_info(AcceleratorType.NVIDIA_CUDA, ModelSize.SMALL)
print(info.get("tools"))
```

### Dependency checks and doctor reports

Dependency checks can be composed and reported without performing repairs:

```python
from Hestia.software.dependency import DependencyRegistry, SystemCommandDependency
from Hestia.software.doctor import Doctor

registry = DependencyRegistry()
registry.register(SystemCommandDependency("git"))
report = Doctor(registry).run()
print(report.to_dict())
```

The registry does not scan the machine for all installed software.
Applications choose the requirements to register. Command version
queries run only when the caller configures the arguments, and use a timeout;
the parser is optional.

### Software inventory

Independently, `Hestia.detect_software()` inventories the configured CLI
catalog; see the package README for version-probe behavior and limitations.

### Installation

The installer accepts only caller-defined install requests and injected
backends. Execution requires caller-supplied authorization scoped to the
approved dependency group/actions. Hestia does not prompt for approval, select
packages, choose a package manager, or provide a default backend; authorization
is an application-level scope check, not a security boundary. Doctor reports
health and caller-provided diagnostics without repairs; its `repair()` method
delegates an already-built plan to the same installer path. An injected backend
or service probe must enforce the timeout passed to it; Hestia does not
interrupt it automatically.

#### Installation progress

Create an `InstallProgressTracker` from `Hestia.software.installer` and pass
it as `progress=tracker` to `Installer.execute()` or `Doctor.repair()`.
`tracker.actions` is a thread-safe snapshot keyed by action ID. Each event's
`completed` is a backend-reported fraction from 0 to 1, or `None` when unknown;
terminal events carry an action status. Execute on a worker thread to inspect
progress concurrently. Fractions depend on backend measurements; Hestia does
not estimate unknown percentages. Action success reaches 1.0 before dependency
rechecks, so use the returned report for overall success. Invalid fractions
are ignored and recorded in `progress_errors`.

### Examples

Runnable model and software examples are in `examples/python/models/` and
`examples/python/software/`. CLI examples are in `examples/python/cli/`.

## Running Tests

```bash
cd python
pytest
```

`tools/run_tests.py` delegates to each `tools/<subpackage>/run_tests.py` and collects output in
`tests/test_output.txt`. `tests/test_examples.py` runs every script under
`examples/python/`.

### Windows

Alternatively, use `scripts/run_tests.bat`.

### macOS and Linux

Alternatively, use `scripts/run_tests.sh`.

## Scripts and Tools

### Python tools

| Item | Purpose |
|---|---|
| `tools/run_tests.py` | Runs each sub-package's `run_tests.py`. |
| `tools/clean.py` | Uninstalls the package, runs each sub-package's `clean.py`, then removes `build`, `dist`, caches, `egg-info` and `__pycache__`. Supports `--dry-run` and `-y`. |
| `tools/models/run_tests.py` | Runs the models tests and the examples test. |
| `tools/hardware/run_tests.py` | Runs hardware detection and recommendation tests. |
| `tools/software/run_tests.py` | Runs inventory, dependency, installer, and doctor tests. |
| `tools/models/clean.py` | Cleans models-related artifacts. |
| `tools/hardware/clean.py` | Cleans hardware-related artifacts. |

To add a sub-package, create `tools/<name>/clean.py` (picked up
automatically by `clean.py`) and add the name to `SUITES` in
`tools/run_tests.py`.

### Windows wrappers

`scripts/run_tests.bat` runs the test suite through `tools/run_tests.py`;
`scripts/clean.bat` runs `tools/clean.py`.

### macOS and Linux wrappers

`scripts/run_tests.sh` runs the test suite through `tools/run_tests.py`;
`scripts/clean.sh` runs `tools/clean.py`.

## Versioning / Metadata

Name, version, description, license, authors, homepage and `requires-python`
come from `project.ini` through `setup.py`; do not
hardcode them in `pyproject.toml`. The pre-commit hook checks the version
against the Doxyfile `PROJECT_NUMBER`.
