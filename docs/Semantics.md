@page Semantics Semantics


This document captures the behavioral guarantees of the active Python
implementation and the intended contract for future implementations. The C++
tree is not yet implemented, so software guarantees below are currently
Python-only.

## Why This Document Exists

`Concepts.md` describes what things are; this document describes how they must
behave, so contributors know what to preserve and tests can assert the same
outcomes.

## Guarantees

### Boundary

- Hardware and model APIs report capabilities and advisory recommendations.
  Hestia does not manage model processes, download models, or run inference.
- Software checks are read-only. Installation can change the environment only
  through an explicitly requested action executed by a caller-supplied backend.
- Hestia was abstracted from, but never imports Domus-AI or its subsystems.
- `Hestia.models` never imports `Hestia.hardware` (or `software`).
- The three information areas are independently callable.

### Catalog lookup

- **Tier resolution:** `get_tier(accelerator, size)` returns the exact entry
  when present. Otherwise it tries the tiers in the order `LARGE`, `MEDIUM`,
  `SMALL`, `TINY` for the same accelerator and returns the first that exists.
  If the accelerator has no entry at all, it returns the CPU `MEDIUM` entry.
  It never raises for any valid enum combination.
- **Required keys:** every catalog entry contains `models`, `thinking`,
  `tools`, `vision`, `quantization`, `batch_size`, `context` and `performance`.
- **Unknown categories:** `get_category(entry, name)` returns an empty list
  for a category the entry does not have.
- **Model info:** `get_model_info(accelerator, size)` returns one immutable
  `ModelInfo` using the same resolution rules as `get_tier()`. If either
  argument is omitted it returns a list of all matching entries. Result
  ordering follows the catalog order.
- **Serialization:** `ModelInfo.to_dict()` serializes enums to their string
  `value`, and category lists are copies, so callers cannot mutate the catalog.

### Compatibility

- `Hestia.model_catalog` remains importable and exposes the same names as
  `Hestia.models.catalog`.
- Enum values (for example `"nvidia_cuda"`, `"tiny"`) are part of the public
  contract and do not change within a `0.3.x` release.

### Hardware detection

These apply to the implemented hardware package:

- Each CPU, memory, platform, and GPU probe is best-effort; unavailable data
  degrades to documented defaults and does not invalidate unrelated fields.
- Optional tools and libraries (NVML, `rocm-smi`, PowerShell and
  `system_profiler`) being absent is not an error.
- GPU discovery never runs through a shell, and each subprocess probe has a
  timeout.
- `available_for_models_gb` uses 70% of available RAM as headroom and caps it
  at 80% of reported free memory on the selected accelerator when available.
  It is an estimate, not a runtime guarantee.
- A recommendation is advisory catalog data. It does not confirm that a
  runtime supports or has installed a listed model.

### Software dependencies, doctor, and installer

- `DependencyRegistry` checks only dependencies explicitly registered by the
  caller, in registration order. Supported built-in checks cover Python
  distributions, commands on `PATH`, files, directories, and environment
  variables. Service, system-library, driver, and custom checks require
  caller-provided probes.
- A command version query runs only when the caller provides fixed arguments
  and an optional parser; it uses a timeout and does not search for or execute
  arbitrary commands. Missing, failed, timed-out, and unknown checks are
  reported as structured statuses. A version constraint without a valid,
  reported version is unknown, not guessed.
- `Doctor.run()` aggregates selected dependency checks and caller-provided
  diagnostics. Its `healthy` result is false for a required unsatisfied
  dependency or an error-severity diagnostic; warnings alone do not make it
  unhealthy. `DoctorReport.failed_dependencies` lists every unsatisfied
  dependency result in report order, including optional dependencies. Its
  `to_dict()` form contains a JSON-friendly list. Running a doctor report never
  installs or repairs software.
- `Installer.plan()` accepts caller-defined actions for registered
  dependencies and skips dependencies already satisfied. `Installer.execute()`
  requires authorization matching the plan group and every action ID, then
  invokes only the named injected backends and rechecks affected dependencies.
- Missing backends, backend failures, timeouts, and recheck results are
  reported. Hestia supplies no default package-manager backend, package
  selection policy, privilege escalation, or security sandbox. The
  authorization object is a caller approval scope, not a security credential.
  `InstallReport.failed_dependencies` lists names in action order followed by
  any additional unsatisfied rechecks, with duplicates removed; it includes
  unsuccessful actions even if a later check reports the dependency satisfied.
  Its `to_dict()` form contains a JSON-friendly list. Installer timeouts are
  passed to the backend, which must enforce them; Hestia reports a timeout if
  the backend raises `TimeoutError`. Service probes likewise enforce their own
  supplied timeout.
- These APIs are not a general inventory of installed software. Only
  caller-configured dependencies are checked. Whole-system software analysis
  is planned for the next implementation phase, which will add a software
  catalog.

## Explicitly Out of Scope

Allowed to differ: performance, internal log messages, and the specific model
names in the catalog between releases.

## Testing This Contract

`python/tests/test_models.py` covers the catalog guarantees and the import
boundary. `python/tests/test_software.py` covers dependency, installer, and
doctor behavior. `python/tests/test_hardware.py` and
`python/tests/test_recommender.py` cover detection and recommendation using
mocks and synthetic data. `python/tests/test_examples.py` runs every example.
CI must not depend on any specific hardware.
Run them with `python/scripts/run_tests.bat` or `.sh`.
