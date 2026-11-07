# Examples

Runnable, minimal usage examples for both implementations, kept at the repo
root (rather than nested inside `cpp/` or `python/`) so they're easy to find
and compare side-by-side. See [`../docs/Architecture.md`](../docs/Architecture.md)
for the reasoning.

- [`cpp/`](cpp/) — examples using the C++ implementation (built against `../cpp/src`).
- [`python/`](python/) — examples using the Python implementation (built against `../python/src`).

Each example should be small and focused on demonstrating one concept from
[`../docs/Concepts.md`](../docs/Concepts.md). Keep the C++ and Python examples
conceptually parallel (same scenario, both languages) wherever practical, so
it's easy to see that the two implementations behave the same way.

Python hardware examples demonstrate profile detection, serialization and
reporting; recommendation examples show how to pair a profile with the model
catalog. Hardware probes are best-effort, so examples also run on CPU-only
systems without optional GPU interfaces.
