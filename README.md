# Hestia

@page repository_readme Repository README

System discovery, hardware analysis, reusable software dependency checks, and AI model recommendations. Python is the active implementation; the C++ tree is not yet implemented.

> Hestia was developed by abstracting hardware and AI model recommendations from [Domus-AI](https://github.com/nomadiidamon/Domus-AI) and has been expounded on for a fully reusable tool.

## Quick Start

### C++

**C++ has not yet been implemented.**

### Python

```bash
cd python
pip install -e .
```

The Python package also provides read-only, caller-configured dependency
checks, doctor reports, and installation workflows that require caller-defined
requests, injected backends, and explicit authorization. It does not yet
provide whole-system software analysis; a catalog-based inventory is planned
for the next implementation phase. It does not choose packages or package
managers or install or repair anything during a check or report. See the [Python implementation
guide](https://nomadiidamon.github.io/Hestia/python_implementation.html) for supported checks and limits.

## Documentation

| Doc | Purpose |
|---|---|
| [Architecture](https://nomadiidamon.github.io/Hestia/Architecture.html) | How the repo is structured and why |
| [Concepts](https://nomadiidamon.github.io/Hestia/Concepts.html) | Core concepts for the active Python implementation and future C++ work |
| [Semantics](https://nomadiidamon.github.io/Hestia/Semantics.html) | Python behavioral guarantees and the intended contract for future implementations |

## Shared Metadata

Project-wide values (version, contributors, project name, etc.) live in a single place: [`project.ini`](project.ini). The Python build reads this file; C++ tooling should use it when that implementation is added.

## Contributing

PRs welcome. See [Semantics](https://nomadiidamon.github.io/Hestia/Semantics.html) before changing observable Python behavior; use it as the intended contract for future C++ work.

