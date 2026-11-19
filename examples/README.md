# Examples

@page examples Examples

Minimal usage examples kept at the repo root (rather than nested inside `cpp/`
or `python/`). Python examples are runnable and covered by the test suite; the
C++ implementation is not yet implemented. See
[Architecture](https://nomadiidamon.github.io/Hestia/Architecture.html) for the repository layout.

## Example locations

- `examples/cpp/` — examples for the C++ implementation placeholder.
- `examples/python/` — runnable examples using the Python implementation and `python/src/`.

Each example should be small and focused on one concept from
[Concepts](https://nomadiidamon.github.io/Hestia/Concepts.html). Keep examples aligned across
languages when a C++ implementation exists.

## Hardware examples

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

The software examples cover configured read-only dependency checks,
caller-authorized installer workflows, and doctor diagnostics with delegated
repair. Installation backends are in-memory demonstrations and do not modify
the host system. The library provides no default package-manager backend.
Configured CLI inventory is available separately; it is not an exhaustive
installed-software scan. See [Software inventory](../python/README.md#software-inventory)
for its scope. Checks do not repair anything.

## Running Python examples

Run one Python example area with `examples/python/run_hardware.py`,
`run_models.py`, `run_recommendations.py` or `run_software.py`. Run
`examples/python/run_all.py` to run all four area runners. The matching
`python/scripts/run_hardware_examples`, `run_models_examples`,
`run_recommendations_examples` and `run_software_examples` wrappers are
available for each platform; `run_examples` runs all areas. The wrappers set `PYTHONPATH` and pause before
exiting. When running Python scripts directly, set `PYTHONPATH` to `python/src`
or install the package first.

### Windows

Use the `.bat` wrappers.

### macOS and Linux

Use the `.sh` wrappers.
