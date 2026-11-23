@page python_package_readme Hestia for Python

# Hestia for Python

Hestia provides system discovery, hardware analysis, reusable software
dependency checks, and AI model recommendations. Its Python package provides
hardware profiles and reusable dependency, doctor, and installer frameworks.
These software frameworks are Python-only; C++ is not implemented.

The distribution is named `hestia-system`; import it as `Hestia`.
The Python package depends on `auctor-utils` for diagnostics and terminal utilities.

## Installation

```bash
python -m pip install hestia-system
```

Optional dependencies are available as extras:

```bash
python -m pip install "hestia-system[nvidia]"  # NVIDIA telemetry support
python -m pip install "hestia-system[dev]"     # pytest
```

## Command-line interface

The `hestia` command provides independent hardware, software, and model
catalog views:

```bash
hestia scan
hestia hardware
hestia software --no-version-probes
hestia models
hestia recommend
hestia report
```

Commands print readable text by default. Add `--json` after any command for
machine-readable output:

| Command | JSON output |
|---|---|
| `hardware` | Hardware profile |
| `software` | Configured software profile |
| `models` | List of model catalog entries |
| `recommend` | Model recommendation for detected hardware |
| `report` | Hardware profile and its model recommendation |
| `scan` | Hardware and configured software profiles |

Software discovery runs version commands for the configured catalog by
default; a discovered executable may have side effects. Use
`--no-version-probes` with `software` or `scan` to avoid executing those
commands. `hestia --help` lists all commands and options. The same interface is
available as `python -m Hestia.cli`.
Text catalog and recommendation output groups models by category, with one
model per bullet. Hardware and software profiles show each GPU or tool as a
separate record; JSON output preserves these records as nested objects and
arrays.
Human-readable output uses color when Auctor detects a compatible terminal;
redirected output and JSON remain plain text.

The example runner at `python/scripts/run_examples.sh` uses the workspace
source. When running examples directly, install the checkout in editable mode
with `python -m pip install -e ./python` from the repository root; otherwise
Python may use an older installed Hestia. The CLI text report example is
`examples/python/cli/cli_02_report_text.py`; the JSON example is uncolored.

## Diagnostics

Hestia uses standard Python loggers under `Hestia`. To additionally record
their messages using Auctor Livy, configure a log file explicitly:

```python
import Hestia

Hestia.configure_logging("logs/hestia.log")
try:
  profile = Hestia.detect_hardware()
finally:
  Hestia.shutdown_logging()
```

Configuration does not disable standard logging propagation. Reconfiguring
closes the previous Livy route, and importing Hestia does not create log files.
The optional `level` argument accepts Python logging levels and defaults to
`logging.DEBUG`.

`InstallProgressTracker` records the latest event for each action and displays
an Auctor spinner on terminals. It shows percentages only when the backend
reports a fraction, or when an action completes successfully. Pass
`display=True` or `display=False` to override terminal detection, and `stream`
to select the output stream. Installation backends must supply intermediate
fractions for real-time percentage updates.

## Usage

### Hardware and model overview

```python
from Hestia import AcceleratorType, ModelSize, get_model_info
import Hestia

info = get_model_info(AcceleratorType.NVIDIA_CUDA, ModelSize.SMALL)
print(info)

profile = Hestia.detect_hardware()
recommendation = Hestia.recommend_model(profile)
Hestia.print_hardware_report(profile, recommendation)
```

### Model recommendations

This example uses the hardware `profile` from
[Hardware and model overview](#hardware-and-model-overview).

For constrained recommendations, pass `ModelRecommendationWeight` to
`recommend_model()`; capabilities and model families are separate filters.
For example:

```python
from Hestia.models import ModelRecommendationWeight, recommend_model

weight = ModelRecommendationWeight(
    max_memory_gb=6, max_parameters_billions=8,
    include_capabilities={"tools"}, exclude_families={"llama3.1"},
)
recommendation = recommend_model(profile, weight)
```

Memory filtering is an estimate of model weights, not a runtime limit or a
guarantee that a model fits. See `docs/Semantics.md` for tier ranges, filter
semantics, and the estimation formula. For custom entries, construct a
`ModelCatalog` and pass it to `ModelRecommender(..., catalog=...)`; the legacy
`MODEL_DATABASE` is a separate snapshot.

### Hardware profile

GPU free memory is `None` when a probe cannot measure it, and `0.0` when
measured as zero. The model-memory estimate falls back to available system RAM
when the selected accelerator has no known free-memory measurement.

Intel GPU UUIDs are obtained from the optional Level Zero runtime when the
device can be matched unambiguously by PCI address. A UUID is not guaranteed
to be a persistent hardware serial number.
AMD GPU UUIDs are similarly obtained through the optional HIP runtime, when
its beta UUID API supports the device. Both runtimes must be discoverable by
the system library loader; otherwise UUIDs remain unknown.

#### Windows

`pnp_device_id` contains the device instance ID when available; it is distinct
from a GPU UUID. A PCI address omits the domain when Windows reports only a
single-segment bus location, unless Level Zero or HIP supplies it.

#### macOS

The CPU brand is read from `sysctl` when Python reports only a
generic architecture name. Apple GPU memory is shared with system RAM, so the
profile uses a memory amount only when `system_profiler` reports one; otherwise
total GPU memory is 0 GB and free GPU memory is unknown. When a Metal device
can be uniquely matched by name to a `system_profiler` GPU, three additional
fields are available:

- `metal_recommended_working_set_gb`: Metal's estimated performance threshold,
  not dedicated or free VRAM and not used in the model-memory estimate.
- `metal_gpu_families`: the highest supported family in each checked group
  (Apple 1-10, Mac 1-2, Common 1-3, and Metal 3-4), not CUDA compute capability.
- `metal_registry_id`: a Metal registry identifier, not a UUID or guaranteed
  persistent hardware identifier.

These fields are `None` when unavailable or ambiguous. A family list can be
empty when none of the checked families are supported. Apple silicon GPUs do
not expose PCI/PNP identifiers through this probe, and macOS does not report a
separate graphics driver version here.

### Software inventory

The configured CLI inventory is independent of dependency checks:

```python
import Hestia

profile = Hestia.detect_software(probe_versions=False)
for tool in profile.tools:
    print(tool.name, tool.present, tool.executable_path, tool.version_status.value)
```

The default catalog covers Git, Python, and Ollama. It searches only configured
executable names on `PATH`, in alias order, and includes missing tools. Supply a
sequence of `Hestia.software.SoftwareDefinition` objects as `catalog` to replace
the default catalog. Aliases must be command names, not paths. Lookup uses
Python's `shutil.which`. Names must be unique ignoring case. Version probes are
enabled by default, execute the discovered program with configured arguments,
and have a per-tool timeout (five seconds by default). A configured executable
can have side effects; use `probe_versions=False` to avoid executing it.
Missing tools, unsupported probes, unrecognized versions, failures, and
timeouts are reported separately in `version_status`; a failed probe does not
make a found executable absent.
`profile.to_dict()` produces a JSON-friendly snapshot in catalog order. This is
not an exhaustive inventory of installed applications or evidence that a
runtime is healthy or compatible with a model.

#### Platform-specific catalog rules

A definition may replace its default aliases and version rules for specific
`sys.platform` values:

```python
from Hestia.software import SoftwareCommand, SoftwareDefinition

parse_version = lambda output: output.strip() or None
tool = SoftwareDefinition(
    "example", ("example",), ("--version",), parse_version,
    platform_commands={
        "win32": SoftwareCommand(("example-cli",), ("version",), parse_version),
    },
)
profile = Hestia.detect_software((tool,))
```

The matching platform command replaces the default completely; if it is
missing, discovery does not retry the default. Platforms without an override
use the default. Probe output is decoded using the platform's default encoding
with replacement for undecodable bytes, which may leave the version unknown.

#### Windows

`shutil.which` has platform-specific current-directory behavior. Windows batch
files are not version-probed.

### Dependency checks and doctor reports

Only caller-registered dependencies are checked. Built-in checks cover Python packages,
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

### Installation

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

#### Installation progress

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

## Requirements

The package supports Python versions declared by the project metadata (Python
3.10 and later).

## Development

From the repository checkout:

```bash
cd python
python -m pip install -e ".[dev]"
python -m pytest
```

### Package metadata

Package metadata is maintained in the repository's `project.ini`. Source
distributions include a copy of that file so they can be built independently
of the repository checkout.


## Documentation

For full python documentation, visit [Hestia](https://nomadiidamon.github.io/Hestia/python_implementation.html)