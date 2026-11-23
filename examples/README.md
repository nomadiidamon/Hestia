# Examples

@page examples Examples

Minimal usage examples kept at the repo root (rather than nested inside `cpp/`
or `python/`). Python examples are runnable and covered by the test suite; the
C++ implementation is not yet implemented. See
[Architecture](https://nomadiidamon.github.io/Hestia/Architecture.html) for the repository layout.

## Example locations

- `examples/cpp/` - examples for the C++ implementation placeholder.
- `examples/python/` - runnable examples using the Python implementation and `python/src/`.

Each example should be small and focused on one concept from
[Concepts](https://nomadiidamon.github.io/Hestia/Concepts.html). Keep examples aligned across
languages when a C++ implementation exists.

## Hardware examples

Examples with both output formats use separate scripts. JSON scripts print one
JSON value; text scripts print a human-readable report. The format pairs are:

| Area | Text | JSON |
|---|---|---|
| Hardware | `hardware_02_report.py` | `hardware_01_profile.py` |
| Simulated GPUs | `hardware_03_simulated_gpus.py` | `hardware_04_simulated_gpus_json.py` |
| Model enums | `models_01_enums.py` | `models_13_enums_json.py` |
| Model categories | `models_05_get_category.py` | `models_10_category_json.py` |
| Model information | `models_06_model_info.py` | `models_11_model_info_json.py` |
| Custom model catalog | `models_09_custom_catalog.py` | `models_12_custom_catalog_json.py` |
| Recommendation | `recommendation_01_basic.py` | `recommendation_03_basic_json.py` |
| Constrained recommendation | `recommendation_02_constraints.py` | `recommendation_04_constraints_json.py` |
| Dependency checks | `software_01_dependency_checks.py` | `software_09_dependency_checks_json.py` |
| Installer | `software_02_installer.py` | `software_10_installer_json.py` |
| Doctor | `software_03_doctor.py` | `software_11_doctor_json.py` |
| Software profile | `software_04_detection.py` | `software_05_profile.py` |
| Custom software catalog | `software_06_catalog.py` | `software_08_catalog_json.py` |
| CLI report | `cli_02_report_text.py` | `cli_01_report_json.py` |

Python hardware examples demonstrate profile detection, serialization and
reporting. Hardware probes are best-effort, so examples also run on CPU-only
systems without optional GPU interfaces.
The simulated GPU example also shows a multi-GPU profile, using the same report
function as real detection. Simulated devices do not establish that the
corresponding runtime is installed.

### Windows

The simulated GPU example includes an integrated Windows detection fallback.

## Model and recommendation examples

Recommendation examples show how to pair a hardware profile with the model
catalog. See [Hardware examples](#hardware-examples) for profile detection.

## Software examples

The software examples cover configured command inventory, profile serialization,
custom software catalogs, read-only dependency checks, caller-authorized
installer workflows, and doctor diagnostics with delegated repair. Installation
backends are in-memory demonstrations and do not modify the host system. The
library provides no default package-manager backend. Configured CLI inventory
is not an exhaustive installed-software scan. See
[Software inventory](../python/README.md#software-inventory) for its scope.
Checks do not repair anything.
The `software_07_install_progress.py` example simulates an installation for
at least 15 seconds, with a live spinner on a terminal and progress lines when
redirected. It only changes in-memory state, and runs as part of the software
and all-example runners.

## CLI examples

`examples/python/cli/cli_01_report_json.py` runs the Hestia report command
through its Python module entry point and prints JSON; `cli_02_report_text.py`
shows the formatted text report. Run the examples directly or use
`examples/python/run_cli.py`.

## Running Python examples

Run one Python example area with `examples/python/run_hardware.py`,
`run_models.py`, `run_recommendations.py`, `run_software.py` or `run_cli.py`.
Run `examples/python/run_all.py` to run all five area runners. The matching
`python/scripts/run_hardware_examples`, `run_models_examples`,
`run_recommendations_examples` and `run_software_examples` wrappers are
available for each platform; `run_examples` runs all areas. The wrappers set
`PYTHONPATH` and pause before exiting. When running Python scripts directly,
set `PYTHONPATH` to `python/src` or install the package first.

### Windows

Use the `.bat` wrappers.

### macOS and Linux

Use the `.sh` wrappers.
