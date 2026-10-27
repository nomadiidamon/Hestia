# Contributing Guidelines

## Introduction

Thank you for your interest in contributing! This document outlines the guidelines and best practices for contributing to this project, which provides parallel C++ and Python implementations.

### Code of Conduct

All contributors are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Repository Model

This repository separates **implementation** from **shared semantics and concepts**:

- **Shared concepts and semantics** live in [`docs/concepts.md`](docs/concepts.md) and [`docs/semantics.md`](docs/semantics.md). They define what the project is and the behavior every implementation must uphold.
- **Implementations** live in independent trees, each with its own idiomatic tooling:
  - [`cpp/`](cpp/) - built with premake5. See [`docs/cpp/README.md`](docs/cpp/README.md).
  - [`python/`](python/) - packaged with `pyproject.toml`. See [`docs/python/README.md`](docs/python/README.md).
- **Shared metadata** (version, contributors, etc.) lives once in [`project.ini`](project.ini).
- **Examples** mirror the language split under [`examples/`](examples/).

See [`docs/architecture.md`](docs/architecture.md) for the full layout.

### Ground Rules

- A change to behavior starts in `docs/semantics.md` (or `docs/concepts.md`), then is applied to every implementation. If you only touch one language, say so in your PR and open a follow-up issue for the other.
- Do not introduce cross-language build dependencies. Each language keeps its native tooling.
- Do not duplicate project-wide metadata; update `project.ini`.
- Keep docs and examples in the matching language subtree.

## Getting Started

1. **Fork the Repository** using the "Fork" button on the repository page.
2. **Clone Your Fork**:
```bash
git clone --recursive https://github.com/<your-user>/<repo-name> <desiredLocation>
```
3. **Set Up the Development Environment** for the language(s) you are working on (see below).
4. **Create a Branch** with a descriptive name for your feature or fix.
5. **Make Changes** following the coding standards and naming conventions below.
6. **Test Your Changes**: run existing tests and add new ones where needed.
7. **Commit** with clear, concise messages in small, focused commits.
8. **Push** to your fork.
9. **Open a Pull Request** describing the problem, the solution, and which implementations are affected.
10. **Address Feedback**: maintainers may request changes. Be open to feedback and responsive.
11. **Merge**: once approved, a maintainer will merge your changes.

## Development Setup

### C++

```bash
cd cpp
premake5 <action>   # e.g. vs2022, gmake2
```

Format code with `cpp/scripts/format.sh`.

### Python

Python 3.9 or newer is required. From the `python/` directory, create a virtual environment and install the package in editable mode **with the `dev` extra**, which installs the development dependencies (pytest, linters/formatters, etc.) defined under `[project.optional-dependencies]` in `python/pyproject.toml`:

```bash
cd python
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
```

Run the tests with `pytest` and format code with `python scripts/format.py`.

## Naming Conventions

### C++

- Snake_Case/snake_case/snake_Case is fine for private member or local variables.
- camelCase is fine for public member or local variables, although `Name` is preferred to something like `myName`.
- Functions should always be PascalCase - `DoThing()` - unless it is a variant - `DoThing_Internal()` - in which case Snake_Case is fine.

Examples:
- Class member variables (private): `m_name`, `m_array`, etc.
- Class member variables (public): `Name`, `myName`, `Length`, `applicationConfig`, etc.
- Class functions (private): `DoThing()`, `DoThing_Internal()`, etc.
- Class functions (public): `DoThing()`, `DoThingAgain()`, etc.
- Class static variables (private): `s_name`, `s_array`, etc.
- Class static variables (public): `sName`, `sArray`, etc.
- Boolean values: `bHasAccess`, `b_Access`, etc.

### Python

Follow [PEP 8](https://peps.python.org/pep-0008/):

- Modules and packages: `lower_snake_case` (short, no hyphens).
- Classes and exceptions: `PascalCase` (`CapWords`).
- Functions, methods, variables, and arguments: `snake_case`.
- Constants: `UPPER_SNAKE_CASE`.
- Non-public members and helpers: single leading underscore (`_internal_value`, `_do_thing()`).
- Name-mangled attributes: double leading underscore only when truly needed.
- Booleans: read as predicates (`is_valid`, `has_access`).
- Add type hints to public APIs and docstrings to public modules, classes, and functions.

### Cross-Language Parity

Equivalent public concepts should be recognizably the same across implementations (e.g. C++ `DoThing()` corresponds to Python `do_thing()`). Each language uses its own conventions rather than copying the other's.

## Coding Standards

- Follow the existing style of the language tree you are editing.
- Use clear, descriptive names.
- Comment only where the code cannot explain itself, such as complex logic or non-obvious constraints.
- Keep code modular and reusable; avoid duplication.
- Write unit tests for new features and bug fixes in each affected implementation.
- Ensure behavior matches [`docs/semantics.md`](docs/semantics.md).
- Update docs and examples when public behavior changes.
