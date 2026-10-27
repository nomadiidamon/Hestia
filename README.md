# Project Name

> One-line description of what this project does.

A dual-language implementation provided in both **C++** and **Python**, sharing
the same design, semantics, and versioning, under one repository.

## Repository Layout

```
.
├── cpp/                  # C++ implementation (premake5)
│   ├── src/
│   ├── scripts/
│   └── tool/
├── python/               # Python implementation (pyproject.toml)
│   ├── src/
│   ├── scripts/
│   └── tool/
├── examples/             # Usage examples for both languages
│   ├── cpp/
│   └── python/
├── docs/                 # Shared + per-language documentation
│   ├── architecture.md
│   ├── concepts.md
│   ├── semantics.md
│   ├── cpp/README.md
│   └── python/README.md
├── .github/workflows/    # CI: build + documentation
├── project.ini           # Shared metadata read by both languages
├── LICENSE
└── README.md
```

## Quick Start

### C++

```bash
cd cpp
premake5 gmake2   # or vs2022, xcode4, etc.
make -C build
```

See [`docs/cpp/README.md`](docs/cpp/README.md) and
[`examples/cpp/`](examples/cpp/) for details.

### Python

```bash
cd python
pip install -e .
```

See [`docs/python/README.md`](docs/python/README.md) and
[`examples/python/`](examples/python/) for details.

## Documentation

| Doc | Purpose |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | How the repo is structured and why |
| [`docs/concepts.md`](docs/concepts.md) | Core concepts shared by both implementations |
| [`docs/semantics.md`](docs/semantics.md) | Behavioral guarantees both languages must uphold |
| [`docs/cpp/README.md`](docs/cpp/README.md) | C++-specific build/dev notes |
| [`docs/python/README.md`](docs/python/README.md) | Python-specific build/dev notes |

## Shared Metadata

Project-wide values (version, contributors, project name, etc.) live in a single
place: [`project.ini`](project.ini). Both the C++ and Python build tooling read
from this file so version numbers and metadata never drift apart. See
`docs/architecture.md` for how each side is expected to consume it.

## Contributing

PRs welcome. Please keep behavior parity between the C++ and Python
implementations — see `docs/semantics.md` before changing observable behavior
in either language.

## License

See [`LICENSE`](LICENSE).
