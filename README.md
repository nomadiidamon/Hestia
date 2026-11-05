# Hestia

System discovery, hardware and software analysis, and AI model recommendations. A dual-language implementation provided in both **C++** and **Python**, sharing the same design, semantics, and versioning, under one repository.

> Hestia was developed by abstracting hardware and AI model recommendations from [Domus-AI](https://github.com/nomadiidamon/Domus-AI) and has been expounded on for a fully reusable tool.

## Quick Start

### C++

**C++ has not yet been implemented.**

### Python

```bash
cd python
pip install -e .
```

## Documentation

| Doc | Purpose |
|---|---|
| [`docs/Architecture.md`](docs/Architecture.md) | How the repo is structured and why |
| [`docs/Concepts.md`](docs/Concepts.md) | Core concepts shared by both implementations |
| [`docs/Semantics.md`](docs/Semantics.md) | Behavioral guarantees both languages must uphold |

## Shared Metadata

Project-wide values (version, contributors, project name, etc.) live in a single place: [`project.ini`](project.ini). Both the C++ and Python build tooling read from this file so version numbers and metadata never drift apart.

## Contributing

PRs welcome. Please keep behavior parity between the C++ and Python
implementations - see [`docs/Semantics.md`](docs/Semantics.md) before changing observable behavior in either language.

