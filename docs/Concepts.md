@page Concepts Concepts


Hestia provides system discovery, hardware analysis, reusable software
dependency checks, and AI model recommendations. This document defines its
core concepts and terminology.

## Overview

Hestia reports hardware capabilities, provides reusable software dependency
checks, and advises on models based on observed hardware. Applications decide
what to do about the results. It covers three independent information areas:

- **Hardware:** CPU, RAM, GPUs/accelerators, VRAM and platform.
- **Software:** caller-configured dependency checks, aggregated health reports,
  and caller-authorized installation through supplied backends.
- **AI models:** a catalog of models suited to each hardware tier, plus
  recommendations.

Each area has its own entry points and can be used without the others. Software
checks are read-only; installation can change the environment only through a
caller-supplied backend and an explicitly authorized request. Hestia does not
choose packages or package managers, manage processes, download models, or run
inference. Software tooling is currently Python-only; C++ is not implemented.

## Core Concepts

### Accelerator

The primary compute device used to run models, represented by
`AcceleratorType`: `NONE` (CPU only), `NVIDIA_CUDA`, `NVIDIA_MPS`, `AMD_ROCM`,
`INTEL_ONEAPI`, `APPLE_METAL` and `QUALCOMM_HEXAGON`. The catalog currently has
data for `NVIDIA_CUDA`, `AMD_ROCM`, `INTEL_ONEAPI`, `APPLE_METAL` and `NONE`.

### Model size (tier)

A memory-based class of model that a machine can run, represented by
`ModelSize`: `TINY`, `SMALL`, `MEDIUM`, `LARGE` and `XLARGE`. The tier is
chosen from the memory available for models, and it selects a catalog entry.

### Model catalog

A static database keyed by accelerator, then by tier. Each entry lists model
names per category (`models`, `thinking`, `tools`, `vision`) and recommended
settings: `quantization`, `batch_size`, `context` and `performance`. Not every
accelerator has every tier (for example Intel has no `XLARGE`, and CPU only
has `TINY` to `MEDIUM`), so lookups fall back (see `Semantics.md`).

### ModelInfo

A typed, immutable view of one catalog entry, returned by `get_model_info()`.

### Hardware profile

A snapshot of the machine: CPU, RAM, a list of GPUs, total VRAM, the primary
accelerator, platform details and the memory available for models.

### Software dependencies and diagnostics

`Hestia.software.dependency` lets applications register named checks for Python
packages, commands, files, directories, environment variables, and
caller-provided service, library, driver, or custom probes. Checks can report
versions and enforce version constraints where a version is available.
`Doctor` combines selected dependency results with caller-provided diagnostics
into a structured report. It reports health; it does not choose or perform
repairs. Its `failed_dependencies` list contains all unsatisfied registered
dependencies, including optional ones; `healthy` is false only for required
unsatisfied dependencies or error-severity diagnostics.

This is not yet whole-system software analysis or an inventory of installed
applications and commands. Catalog-based software inventory is planned for
the next implementation phase. Until then, only dependencies explicitly
registered by the caller are checked. Command checks locate the named command
on `PATH`; they run a version query only when the caller supplies its arguments.
The caller can also supply a parser, and the subprocess is bounded by a timeout.

### Installation

`Installer` plans caller-defined actions against registered dependency results
and executes them only through an injected backend. Execution requires an
authorization scope matching the plan's dependency group and action IDs. A
missing backend is reported as unsupported, and dependency checks are rerun
after actions. The authorization object is an application-level approval
scope, not a security credential or sandbox. `InstallReport.failed_dependencies`
lists names with a failed, timed-out, or unsupported action, or an unsatisfied
post-install recheck. Both report types serialize this field as a list in
`to_dict()`. Installation and service-probe timeouts are passed to the
caller-supplied backend or probe, which must enforce them.

### Recommendation

A model suggestion selected from the catalog based on an observed hardware
profile. Recommendations are advisory; software compatibility is not currently
an input to the recommender.

## Terminology / Glossary

| Term | Meaning |
|---|---|
| Accelerator | The primary compute device, an `AcceleratorType` value. |
| Tier | A `ModelSize` value; a memory-based class of model. |
| Category | A kind of model in a catalog entry (`models`, `thinking`, `tools`, `vision`). |
| Catalog entry | The category lists and settings for one accelerator and tier. |
| Fallback | Resolving a missing accelerator/tier combination to a nearby entry. |
| Facade | The top-level `Hestia` package namespace, which is the stable public API. |

## Relationship to Implementation

| Concept | Python |
|---|---|
| Accelerator, tier | `Hestia.types.AcceleratorType`, `Hestia.types.ModelSize` |
| Catalog | `Hestia.models.MODEL_DATABASE`, `get_tier()`, `get_category()` |
| Catalog entry view | `Hestia.models.ModelInfo`, `get_model_info()` |
| Hardware profile | `Hestia.hardware.HardwareProfile`, `GPUInfo`, `HardwareDetector` |
| Dependency checks | `Hestia.software.dependency` |
| Doctor reports | `Hestia.software.doctor` |
| Caller-authorized installation | `Hestia.software.installer` |
| General software inventory | Not implemented |
| Recommendation | `Hestia.recommender.ModelRecommender`, `ModelRecommendation` |

The C++ implementation is a placeholder; the Python implementation is the
active implementation.
