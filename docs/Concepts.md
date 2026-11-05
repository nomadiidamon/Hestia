@page Concepts Concepts

# Concepts

This document defines the core concepts and terminology of Hestia. Anyone
working in either implementation should be able to read this and understand
the domain model without reading code first.

## Overview

Hestia reports what a machine can do; applications decide what to do about
it. It covers three independent information areas:

- **Hardware:** CPU, RAM, GPUs/accelerators, VRAM and platform.
- **Software:** configured command-line tools found on `PATH`, with versions
  when they can be verified.
- **AI models:** a catalog of models suited to each hardware tier, plus
  recommendations.

Each area has its own data types and entry points and can be used without the
others. Hestia does not manage processes, download models, or run inference.

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

### Software inventory

Structured records of configured CLI tools (name, resolved executable path,
version if known). Only a fixed, configured set of tools is probed.

### Recommendation

A model configuration derived from a hardware profile (and, later, the
software inventory) using the catalog.

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
| Hardware profile | Planned: `Hestia.hardware` |
| Software inventory | Planned: `Hestia.software` |
| Recommendation | Planned (depends on `hardware`) |

The C++ implementation is a placeholder; the Python implementation is the
reference for now.
