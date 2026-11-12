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
`Hestia.software.doctor` frameworks are implemented. General software
inventory, a `hestia` CLI, and software-informed model recommendations are not
implemented. Whole-system software analysis is planned for the next
implementation phase, which will add a software catalog. The legacy
`Hestia.model_catalog` path remains available.

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
|   +-- types.py
|   +-- model_catalog.py   # Legacy path
|   +-- models/
|   +-- hardware/
|   +-- software/          # Dependency, installer, and doctor frameworks
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
source .venv/bin/activate      # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

The build reads `../project.ini`, so install from a full repository checkout.

## Usage

```python
import Hestia
from Hestia import AcceleratorType, ModelSize

info = Hestia.get_model_info(AcceleratorType.NVIDIA_CUDA, ModelSize.SMALL)
print(info.get("tools"))
```

Dependency checks can be composed and reported without performing repairs:

```python
from Hestia.software.dependency import DependencyRegistry, SystemCommandDependency
from Hestia.software.doctor import Doctor

registry = DependencyRegistry()
registry.register(SystemCommandDependency("git"))
report = Doctor(registry).run()
print(report.to_dict())
```

The registry does not yet scan the machine for all installed software. A
catalog-based inventory is planned for the next implementation phase.
Applications currently choose the requirements to register. Command version
queries run only when the caller configures the arguments, and use a timeout;
the parser is optional.

The installer accepts only caller-defined install requests and injected
backends. Execution requires caller-supplied authorization scoped to the
approved dependency group/actions. Hestia does not prompt for approval, select
packages, choose a package manager, or provide a default backend; authorization
is an application-level scope check, not a security boundary. Doctor reports
health and caller-provided diagnostics without repairs; its `repair()` method
delegates an already-built plan to the same installer path. An injected backend
or service probe must enforce the timeout passed to it; Hestia does not
interrupt it automatically.

Runnable model and software examples are in `examples/python/models/` and
`examples/python/software/`.

## Running Tests

```bash
cd python
pytest
```

or use `scripts/run_tests.bat` / `scripts/run_tests.sh`. `tools/run_tests.py`
delegates to each `tools/<subpackage>/run_tests.py` and collects output in
`tests/test_output.txt`. `tests/test_examples.py` runs every script under
`examples/python/`.

## Scripts and Tools

| Item | Purpose |
|---|---|
| `scripts/run_tests.bat`, `.sh` | Run the test suite through `tools/run_tests.py`. |
| `scripts/clean.bat`, `.sh` | Run `tools/clean.py`. |
| `tools/run_tests.py` | Runs each sub-package's `run_tests.py`. |
| `tools/clean.py` | Uninstalls the package, runs each sub-package's `clean.py`, then removes `build`, `dist`, caches, `egg-info` and `__pycache__`. Supports `--dry-run` and `-y`. |
| `tools/models/run_tests.py` | Runs the models tests and the examples test. |
| `tools/hardware/run_tests.py` | Runs hardware detection and recommendation tests. |
| `tools/software/run_tests.py` | Runs dependency, installer, and doctor tests. |
| `tools/models/clean.py` | Cleans models-related artifacts. |
| `tools/hardware/clean.py` | Cleans hardware-related artifacts. |

To add a sub-package, create `tools/<name>/clean.py` (picked up
automatically by `clean.py`) and add the name to `SUITES` in
`tools/run_tests.py`.

## Versioning / Metadata

Name, version, description, license, authors, homepage and `requires-python`
come from `project.ini` through `setup.py`; do not
hardcode them in `pyproject.toml`. The pre-commit hook checks the version
against the Doxyfile `PROJECT_NUMBER`.
