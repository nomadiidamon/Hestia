@page Architecture Architecture


This document describes how this repository is organized and why, so that
anyone adding code, docs, or CI can find - and keep finding - the right place for it.

Hestia provides system discovery, hardware analysis, reusable software
dependency checks, and AI model recommendations (see
[Concepts](https://nomadiidamon.github.io/Hestia/Concepts.html)). Hestia is
extracted from [Domus-AI](https://nomadiidamon.github.io/Domus-AI) but does not depend on it. The Python implementation
is active; C++ is currently a placeholder. Whole-system software analysis is
not implemented yet; a catalog-based inventory is planned for the next
implementation phase.

## Goals

- **One repo, two planned implementations.** Python is active; C++ remains a
  placeholder. Shared semantics describe the intended contract, but software
  dependency tooling currently exists only in Python.
- **No shared build system.** Each language keeps its native tooling
  (premake5 for C++, `pyproject.toml` for Python) rather than forcing both
  through one build graph.
- **One shared source of truth for metadata.** Version, contributors, and
  similar project-wide facts live once, in `project.ini`,
  and implementations should read from it instead of maintaining their own copies.
- **Docs and examples mirror the language split**, so a contributor working
  in one language only ever needs to look in that language's subtree plus
  the shared top-level docs.

## Top-Level Layout

```
.
+-- cpp/
|   +-- premake5.lua        # Build configuration entry point
|   +-- include/            # Include dir for users
|   +-- src/                # Library/application source
|   +-- scripts/            # Dev scripts: build helpers, codegen, formatting
|   +-- tool/               # Standalone CLI tool(s) built from this tree
|
+-- python/
|   +-- pyproject.toml      # Static packaging configuration
|   +-- setup.py            # Reads shared metadata from ../project.ini
|   +-- src/Hestia/         # Package source (see "Python Package Layout")
|   +-- tests/              # pytest suite, including a test that runs every example
|   +-- scripts/            # Dev script wrappers (.bat/.sh) for clean and run_tests
|   +-- tools/              # Dev tools; each sub-package has its own clean/run_tests
|
+-- examples/
|   +-- cpp/                # Example programs using the C++ implementation
|   +-- python/             # Example programs using the Python implementation
|
+-- docs/
|   +-- Architecture.md     # This file
|   +-- Concepts.md         # Core concepts for the active implementation
|   +-- Semantics.md        # Python guarantees and intended future contract
|   +-- cpp/README.md       # C++-specific build/dev/contributor notes
|   +-- python/README.md    # Python-specific build/dev/contributor notes
|
+-- .github/workflows/
|   +-- build.yml            # CI: builds/tests both cpp/ and python/
|   +-- documentation.yml    # CI: validates/publishes docs/
|
+-- project.ini              # Shared metadata: version, contributors, etc.
+-- README.md                # Repo-level overview and quick start
`-- LICENSE
```

## Why Separate `cpp/` and `python/` Trees

Keeping the two implementations in sibling top-level directories (rather than interleaving them, or nesting one inside the other) means:

- Each language's native tooling can assume its own tree is the project root for its purposes - premake5 doesn't need to know Python exists, and `pyproject.toml` doesn't need to know about premake5.
- Per-language CI jobs can use a `working-directory` scoped to just that tree (see `.github/workflows/build.yml`).
- It's obvious, from the top level, that this is a dual-language project and where each language's code lives.

## The `src` / `scripts` / `tool` Split (Per Language)

Both `cpp/` and `python/` follow the same internal three-way split, so the
convention only needs to be learned once:

- **`src/`** - the library or application source itself; what gets built
  and/or published.
- **`scripts/`** - developer-facing scripts that support working on the
  project (build helpers, formatting, codegen, release scripts). Not part of
  the shipped artifact.
- **`tool/`** - standalone CLI tool(s) built from this language's `src/`,
  kept separate so "library" and "thing you run" aren't tangled together.

See the [C++ implementation guide](https://nomadiidamon.github.io/Hestia/cpp_implementation.html)
and [Python implementation guide](https://nomadiidamon.github.io/Hestia/python_implementation.html)
for language-specific details.

In the Python tree, `tools/` (plural) holds the dev tools. `tools/clean.py` and
`tools/run_tests.py` discover and delegate to a `clean.py` / `run_tests.py` in
each sub-package folder (currently `tools/models/`), then handle the
project-wide artifacts and test output themselves. The `scripts/` wrappers just
call these tools.

## Python Package Layout

```
python/src/Hestia/
+-- __init__.py        # Stable public facade
+-- types.py           # Shared enums: AcceleratorType, ModelSize
+-- model_catalog.py   # Legacy import path; re-exports models.catalog
+-- models/            # Implemented: catalog, ModelInfo, get_model_info()
|   +-- catalog.py
|   `-- info.py
+-- hardware/          # CPU, memory, GPU, platform and profile detection
|   +-- cpu.py
|   +-- memory.py
|   +-- gpu.py
|   +-- platform.py
|   +-- profile.py
|   `-- detector.py
|-- recommender.py     # Cross-area hardware + model recommendation
`-- software/          # Python dependency checks, installer, doctor reports
  |-- dependency/    # Typed requirements and read-only checks
  |-- installer/     # Caller-authorized backend execution and rechecks
  `-- doctor/        # Health and diagnostic aggregation
```

Dependency rules:

- `types.py` imports nothing from the package.
- `models/`, `hardware/` and `software/` may import `types.py`, but never each
  other's implementation modules. In particular `models/` must not import
  `hardware/` (a test enforces this).
- `software/doctor/` and `software/installer/` depend on `software/dependency/`.
  Dependency checks are read-only. Installation uses caller-supplied inputs,
  authorization scope, and backends; doctor delegates requested repairs to the
  installer rather than mutating the environment itself.
- These packages do not yet provide whole-system software analysis; a
  catalog-based inventory is planned for the next implementation phase. There
  is no default package-manager backend. Applications define what to check and
  provide installation actions/backends; checks and doctor reports never
  install or repair software implicitly.
- Doctor and installer reports expose `failed_dependencies` as an ordered list
  of names, as well as detailed per-dependency/action results.
- Nothing in Hestia may import Domus-AI or its subsystems.
- Recommendations that combine hardware and models are layered on top of
  these packages, not inside `models/`.

The top-level `Hestia/__init__.py` is the public facade; subpackage
`__init__.py` files re-export their supported names.

## Examples

`examples/` sits at the repo root (not nested inside `cpp/` or `python/`) so it is immediately visible as a top-level concern. Python examples are runnable and test-covered; `examples/cpp/` remains a placeholder until the C++ implementation exists.

Python examples live in per-topic folders (`examples/python/models/` holds one
file per topic, named `models_<number>_<topic>.py`). Each carries a Doxygen
`@example` marker so it is rendered in the generated docs, and
`python/tests/test_examples.py` runs every one of them.

## Shared Metadata: `project.ini`

`project.ini` is the single place where facts that apply to the whole
project - not just one language - are recorded: project name, version,
license, maintainers/contributors, and cross-language compatibility notes
(e.g. minimum C++ standard, minimum Python version).

Python packaging currently reads this file. C++ tooling should read it when
that implementation is added rather than holding a separate copy:

- On the C++ side, `premake5.lua` (or a small helper invoked from it) should parse `project.ini` to populate things like the version string.
- On the Python side, `python/setup.py` parses `project.ini` with `configparser`
  and supplies the version, description, license, `requires-python`, authors,
  homepage and README to setuptools. `pyproject.toml` lists those fields as
  `dynamic` and keeps only static settings (name, dependencies, extras, tool
  config). The distribution name `hestia-system` must match `python_package` in
  `project.ini` by hand, because `name` cannot be dynamic.
- The pre-commit hook `03-match-version` checks that the `project.ini` version
  equals the Doxyfile `PROJECT_NUMBER`.

The exact mechanism is left to each language's build scripts; the contract is: **`project.ini` is authoritative, and implementations should derive project-wide values from it rather than duplicating them by hand.** The Python build reads `../project.ini`, so it only builds from a full repository checkout.

## Documentation Layout

Shared documentation - things true of the project as a whole, independent of language - lives directly in `docs/`: this architecture doc, `Concepts.md`, and `Semantics.md`. Anything specific to building, testing, or contributing to one language's implementation lives in that language's own documentation page, keeping the top-level docs free of implementation details that would otherwise need to be duplicated or kept in sync across two READMEs.

## CI Layout

Two workflows, matching the two cross-cutting concerns of the repo:

- **`build.yml`** - builds and tests `cpp/` and `python/` as independent
  jobs (so one language failing doesn't block visibility into the other).
- **`documentation.yml`** - validates (and optionally publishes) everything
  under `docs/`.

## Adding Something New

A quick reference for "where does this go":

| You're adding... | It goes in... |
|---|---|
| New C++ library code | `cpp/src/` |
| New Python package code | `python/src/` |
| A dev/build helper script (either language) | `<language>/scripts/` |
| A sub-package clean/test tool | `python/tools/<subpackage>/` |
| A new CLI tool | `<language>/tools/` |
| A runnable usage example | `examples/<language>/` |
| A concept/behavior for the active implementation and future C++ work | `docs/Concepts.md` or `docs/Semantics.md` |
| A language-specific build/dev note | `docs/<language>/README.md` |
| A project-wide fact (version, contributor, etc.) | `project.ini` |
