@page Semantics Semantics


This document captures the behavioral guarantees an implementation of Hestia
must uphold. If two implementations ever disagree on something described here,
that is a bug in one of them; this file is the tiebreaker. Today the Python
implementation is the only active one, and it is the reference.

## Why This Document Exists

`Concepts.md` describes what things are; this document describes how they must
behave, so contributors know what to preserve and tests can assert the same
outcomes.

## Guarantees

### Boundary

- Hestia reports capabilities only. It does not manage processes, download
  models, or run inference.
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
  contract and do not change within a `0.2.x` release.

### Hardware and software detection (target behavior)

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

Software behavior applies when the software package is implemented:

- Only configured software tools are probed, each with a timeout; Hestia never
  runs arbitrary programs found on `PATH`.
- An unverifiable tool version is reported as unknown, never guessed.
- Software results have a stable ordering and serialize deterministically.

## Explicitly Out of Scope

Allowed to differ: performance, internal log messages, and the specific model
names in the catalog between releases.

## Testing This Contract

`python/tests/test_models.py` covers the catalog guarantees and the import
boundary. `python/tests/test_hardware.py` and
`python/tests/test_recommender.py` cover detection and recommendation using
mocks and synthetic data. `python/tests/test_examples.py` runs every example.
CI must not depend on any specific hardware.
Run them with `python/scripts/run_tests.bat` or `.sh`.
