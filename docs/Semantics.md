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
- Importing `Hestia.models` does not import `Hestia.hardware` or `software`;
  detecting hardware through the recommendation helper loads hardware on demand.
- The three information areas are independently callable.

### Catalog lookup

- **Tier resolution:** `get_tier(accelerator, size)` returns the exact entry
  or the nearest smaller tier for that accelerator, then tries CPU tiers at or
  below the requested tier. A sparse custom catalog raises `LookupError` if
  neither has a suitable entry. The built-in catalog covers every enum pair.
- **Required keys:** the typed catalog supplies empty `models`, `thinking`,
  `tools` and `vision` categories when absent and validates required settings.
- **Legacy views:** `MODEL_DATABASE` is a snapshot for existing callers;
  mutations do not alter the typed catalog. `get_tier()` returns a fresh
  dictionary, and `get_category()` returns a fresh list.
- **Unknown categories:** `get_category(entry, name)` returns an empty list
  for a category the entry does not have.
- **Model info:** `get_model_info(accelerator, size)` returns one immutable
  `ModelInfo` identifying the resolved accelerator and tier. If either
  argument is omitted it returns a list of all matching entries. Result
  ordering follows the catalog order.
- **Serialization:** `ModelInfo.to_dict()` serializes enums to their string
  `value`, and category lists are copies, so callers cannot mutate the catalog.

### Model recommendations

- `ModelRecommendationWeight` can cap available memory, tier and total
  parameters in billions independently. Families are exact case-insensitive
  names before `:`; included capabilities match any listed category, while
  excluded capabilities remove models present in any excluded category.
  Family preferences reorder results without excluding other families.
- Memory selection uses the smaller of the hardware budget and the optional
  cap. Each model's estimated weight memory is parameter billions multiplied by
  one billion and quantization bits divided by eight, plus 25% overhead, then
  divided by 1024^3. Although the API says GB, hardware memory values and these
  estimates use GiB. They are not measured allocations: context, runtime, quantization and
  architecture can require more memory. They cannot guarantee a model fits or
  enforce a runtime memory limit. Unknown parameter counts are excluded.
- Tier thresholds in GB are `<2`, `2-<4`, `4-<12`, `12-<40`, and `40+`.
  Built-in catalog parameter ranges, across all capabilities and accelerators,
  are respectively 0.6-1.8B, 1-3.8B, 1.8-13B, 7-35B and 22-104B.
  These ranges overlap and are descriptive, not tier limits; model tags are
  used as estimates of total parameters, including for MoE models.
- When no entries survive the constraints, the returned lists are empty and
  `reasoning` explains the exclusion. `categories` also includes any custom
  catalog categories.

### Compatibility

- `Hestia.model_catalog` remains importable and exposes the same names as
  `Hestia.models.catalog`.
- Enum values (for example `"nvidia_cuda"`, `"tiny"`) are part of the public
  contract and do not change within a `0.3.x` release.

### Hardware detection

These apply to the implemented hardware package:

- Each CPU, memory, platform, and GPU probe is best-effort; unavailable data
  degrades to documented defaults and does not invalidate unrelated fields.
- Optional tools and libraries (NVML, Intel Level Zero, AMD HIP and `rocm-smi`)
  being absent is not an error. See the platform subsections below for
  additional optional tools.
- GPU PCI vendor and device IDs use lowercase hexadecimal strings such as
  `0x8086` when available.
- PCI bus addresses use hexadecimal `domain:bus:device.function` when the
  domain is known. Unavailable or unrecognized PCI locations remain `None`.
- Intel GPU UUIDs are obtained from Level Zero when available and associated
  by an unambiguous PCI address, not device order. UUIDs may be unavailable
  and should not be assumed to be persistent hardware serial numbers.
- AMD GPU UUIDs are obtained from HIP when available and associated by an
  unambiguous PCI address. The HIP UUID API is beta, and unavailable or
  unsupported devices retain an unknown UUID.
- GPU discovery never runs through a shell, and each subprocess probe has a
  timeout.
- Primary accelerator selection excludes devices marked unavailable.
- `GPUInfo.free_memory_gb` is `None` when unknown (serialized as JSON `null`);
  zero means a measured zero. Callers must handle the optional value.
- `available_for_models_gb` uses 70% of available RAM as headroom and caps it
  at 80% of the smallest known free-memory value among available devices of the
  selected accelerator type, including measured zero. When no such measurement
  exists, it uses the RAM estimate. It is an estimate, not a runtime guarantee.
- The memory estimate is an input to [model recommendations](#model-recommendations).
  A recommendation is advisory catalog data; it does not confirm that a runtime
  supports or has installed a listed model.

#### Windows

- PowerShell being absent is not an error.
- PnP device instance IDs are exposed separately as `pnp_device_id`; they are
  not GPU UUIDs.
- A single-segment PCI location omits the domain, so it is reported as
  `bus:device.function` instead of guessing the domain unless Level Zero or
  HIP supplies the full address.

#### macOS

- `system_profiler` being absent is not an error.

### Software inventory

- `detect_software()` returns one record per configured CLI tool in catalog
  order, including absent tools. It tries executable aliases in order and
  records the first resolved path. The default catalog contains Git, Python,
  and Ollama; a supplied catalog replaces it, and duplicate names ignoring
  case are rejected. Aliases are command names, not paths; resolution follows
  `shutil.which`. This is not a scan of all installed applications.
- Version probes are enabled by default, execute only configured commands and
  arguments without requesting a shell, and use a per-command timeout.
  Disabling probes avoids executing discovered programs. `version_status`
  distinguishes absent tools, disabled or unsupported probes, detected or
  unrecognized versions, failures, and
  timeouts; a found path remains present even if probing fails. Executing a
  configured program may have side effects; this is not a sandbox. Probe output
  uses the platform default text encoding with replacement for undecodable
  bytes; unrecognized versions remain unknown.
- `SoftwareProfile.to_dict()` preserves catalog order and returns JSON-friendly
  tool records with presence, path, version, probe status, and a message.

#### Platform-specific catalog rules

- Definitions may specify a `SoftwareCommand` for an exact `sys.platform`
  value. A matching command replaces the default aliases and version rules,
  even if none of its aliases is found; other platforms use the default. The
  platform mapping is copied and cannot be mutated through the definition.

#### Windows

- `shutil.which` has platform-specific current-directory behavior.
- Windows batch files are not version-probed.

### Software dependency checks

- Dependency checks are independent of [software inventory](#software-inventory)
  and only caller-configured dependencies are checked.
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
- Service probes enforce their own supplied timeout.

### Doctor reports

- `Doctor.run()` aggregates selected dependency checks and caller-provided
  diagnostics. Its `healthy` result is false for a required unsatisfied
  dependency or an error-severity diagnostic; warnings alone do not make it
  unhealthy. `DoctorReport.failed_dependencies` lists every unsatisfied
  dependency result in report order, including optional dependencies. Its
  `to_dict()` form contains a JSON-friendly list. Running a doctor report never
  installs or repairs software.

### Installation

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
  the backend raises `TimeoutError`. For service-probe timeouts, see
  [software dependency checks](#software-dependency-checks).
- `InstallProgressTracker` is a caller-owned, thread-safe callback accepted by
  installer execution and doctor repair. Its `actions` snapshot contains the
  latest event per action. Backend progress is a fraction from 0 to 1 or
  `None` when unknown; invalid fractions are ignored and recorded in
  `progress_errors`. Terminal events identify action success, failure, timeout,
  or unsupported backend. Percentages are backend-reported, not independently
  measured. A successful action reaches 1.0 before the post-install recheck;
  the final report determines whether the installation as a whole succeeded.

## Explicitly Out of Scope

Allowed to differ: performance, internal log messages, and the specific model
names in the catalog between releases.

## Testing This Contract

Tests are grouped under `python/tests/` by topic: `models/` covers catalog
guarantees and recommendation behavior, `software/` covers inventory,
dependency, installer, and doctor behavior, and `hardware/` covers detection.
Platform-dependent tests are nested under each topic's `platform/` directory;
the macOS Metal probe test is under `hardware/platform/macos/`, and the Windows
batch-file test is under `software/platform/windows/`. The root
`test_examples.py` runs every example. CI must not depend on any specific
hardware.

### Windows

Run them with `python/scripts/run_tests.bat`.

### macOS and Linux

Run them with `python/scripts/run_tests.sh`.
