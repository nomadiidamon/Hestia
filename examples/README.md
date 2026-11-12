# Examples

@page examples Examples

Minimal usage examples kept at the repo root (rather than nested inside `cpp/`
or `python/`). Python examples are runnable and covered by the test suite; the
C++ implementation is not yet implemented. See
[Architecture](https://nomadiidamon.github.io/Hestia/Architecture.html) for the repository layout.

- `examples/cpp/` — examples for the C++ implementation placeholder.
- `examples/python/` — runnable examples using the Python implementation and `python/src/`.

Each example should be small and focused on one concept from
[Concepts](https://nomadiidamon.github.io/Hestia/Concepts.html). Keep examples aligned across
languages when a C++ implementation exists.

Python hardware examples demonstrate profile detection, serialization and
reporting; recommendation examples show how to pair a profile with the model
catalog. Hardware probes are best-effort, so examples also run on CPU-only
systems without optional GPU interfaces.

The software examples cover configured read-only dependency checks,
caller-authorized installer workflows, and doctor diagnostics with delegated
repair. Installation backends are in-memory demonstrations and do not modify
the host system. The library provides no default package-manager backend.
Whole-system software analysis is not implemented yet; a catalog-based
inventory is planned for the next implementation phase. Checks do not repair
anything.
