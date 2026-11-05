@page Semantics Semantics

# Semantics

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
  contract and do not change within a `0.1.x` release.

### Hardware and software detection (target behavior)

These apply once the subpackages are ported (see `migration.md`):

- Detection failures degrade to documented defaults instead of raising.
- Optional tools and libraries (NVML, `rocm-smi`, and so on) being absent is
  not an error.
- Only configured software tools are probed, each with a timeout; Hestia never
  runs arbitrary programs found on `PATH`.
- An unverifiable tool version is reported as unknown, never guessed.
- Software results have a stable ordering and serialize deterministically.

## Explicitly Out of Scope

Allowed to differ: performance, internal log messages, and the specific model
names in the catalog between releases.

## Testing This Contract

`python/tests/test_models.py` covers the catalog guarantees and the import
boundary. `python/tests/test_examples.py` runs every example. Detection tests
must use mocks and synthetic data; CI must not depend on any specific hardware.
Run them with `python/scripts/run_tests.bat` or `.sh`.
