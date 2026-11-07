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
| [Architecture](https://nomadiidamon.github.io/Hestia/Architecture.html) | How the repo is structured and why |
| [Concepts](https://nomadiidamon.github.io/Hestia/Concepts.html) | Core concepts shared by both implementations |
| [Semantics](https://nomadiidamon.github.io/Hestia/Semantics.html) | Behavioral guarantees both languages must uphold |

## Shared Metadata

Project-wide values (version, contributors, project name, etc.) live in a single place: [`project.ini`](project.ini). Both the C++ and Python build tooling read from this file so version numbers and metadata never drift apart.

## Contributing

PRs welcome. Please keep behavior parity between the C++ and Python
implementations - see [Semantics](https://nomadiidamon.github.io/Hestia/Semantics.html) before changing observable behavior in either language.

