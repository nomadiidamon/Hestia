@mainpage Hestia

# Hestia

System discovery, hardware analysis, reusable software dependency checks, and
AI model recommendations. Python is the active implementation; C++ is not yet
implemented.

Hestia was developed by abstracting hardware and AI model recommendations from
[Domus-AI](https://nomadiidamon.github.io/Domus-AI/) into a reusable tool.

## Quick Start

### C++

The C++ implementation has not yet been implemented.

### Python

```bash
cd python
pip install -e .
```

Python also provides read-only, caller-configured dependency checks and doctor
reports, plus installation workflows driven by caller-defined requests and
injected backends. Installation requires explicit caller authorization.
Hestia does not yet provide whole-system software analysis; a catalog-based
inventory is planned for the next implementation phase. It does not choose
packages or package managers or install/repair anything as a side effect of a
check or report. See the [Python implementation
guide](https://nomadiidamon.github.io/Hestia/python_implementation.html) for
the supported checks and limits.

## Documentation

- [Architecture](https://nomadiidamon.github.io/Hestia/Architecture.html): repository organization and design.
- [Concepts](https://nomadiidamon.github.io/Hestia/Concepts.html): domain concepts and terminology.
- [Semantics](https://nomadiidamon.github.io/Hestia/Semantics.html): Python behavioral guarantees and intended future contract.

## Community

- [Contributing guidelines](https://nomadiidamon.github.io/Hestia/contributing.html)
- [Code of Conduct](https://nomadiidamon.github.io/Hestia/codeofconduct.html)