# Architecture

This document describes how this repository is organized and why, so that
anyone adding code, docs, or CI can find — and keep finding — the right place
for it.

## Goals

- **One repo, two implementations.** C++ and Python implementations of the
  same project live side by side, with parity in behavior (see
  [`semantics.md`](semantics.md)) but idiomatic, independent tooling per
  language.
- **No shared build system.** Each language keeps its native tooling
  (premake5 for C++, `pyproject.toml` for Python) rather than forcing both
  through one build graph.
- **One shared source of truth for metadata.** Version, contributors, and
  similar project-wide facts live once, in [`project.ini`](../project.ini),
  and both languages read from it instead of maintaining their own copies.
- **Docs and examples mirror the language split**, so a contributor working
  in one language only ever needs to look in that language's subtree plus
  the shared top-level docs.

## Top-Level Layout

```
.
├── cpp/
│   ├── premake5.lua        # Build configuration entry point
│   ├── include/            # Include dir for users
│   ├── src/                # Library/application source
│   ├── scripts/            # Dev scripts: build helpers, codegen, formatting
│   └── tool/               # Standalone CLI tool(s) built from this tree
│
├── python/
│   ├── pyproject.toml      # Build/packaging configuration entry point
│   ├── src/                # Package source
│   ├── scripts/            # Dev scripts: build helpers, release, formatting
│   └── tool/               # Standalone CLI tool(s) built from this tree
│
├── examples/
│   ├── cpp/                # Example programs using the C++ implementation
│   └── python/             # Example programs using the Python implementation
│
├── docs/
│   ├── architecture.md     # This file
│   ├── concepts.md         # Core concepts shared by both implementations
│   ├── semantics.md        # Behavioral guarantees both languages must uphold
│   ├── cpp/README.md       # C++-specific build/dev/contributor notes
│   └── python/README.md    # Python-specific build/dev/contributor notes
│
├── .github/workflows/
│   ├── build.yml            # CI: builds/tests both cpp/ and python/
│   └── documentation.yml    # CI: validates/publishes docs/
│
├── project.ini              # Shared metadata: version, contributors, etc.
├── README.md                 # Repo-level overview and quick start
└── LICENSE
```

## Why Separate `cpp/` and `python/` Trees

Keeping the two implementations in sibling top-level directories (rather than
interleaving them, or nesting one inside the other) means:

- Each language's native tooling can assume its own tree is the project root
  for its purposes — premake5 doesn't need to know Python exists, and
  `pyproject.toml` doesn't need to know about premake5.
- Per-language CI jobs can use a `working-directory` scoped to just that
  tree (see `.github/workflows/build.yml`).
- It's obvious, from the top level, that this is a dual-language project and
  where each language's code lives.

## The `src` / `scripts` / `tool` Split (Per Language)

Both `cpp/` and `python/` follow the same internal three-way split, so the
convention only needs to be learned once:

- **`src/`** — the library or application source itself; what gets built
  and/or published.
- **`scripts/`** — developer-facing scripts that support working on the
  project (build helpers, formatting, codegen, release scripts). Not part of
  the shipped artifact.
- **`tool/`** — standalone CLI tool(s) built from this language's `src/`,
  kept separate so "library" and "thing you run" aren't tangled together.

See `docs/cpp/README.md` and `docs/python/README.md` for the language-specific
details of what currently lives in each.

## Examples

`examples/` sits at the repo root (not nested inside `cpp/` or `python/`) so
that it's immediately visible as a top-level concern, and so example code can
be found and compared side-by-side across languages without digging into
either implementation's tree. Each subdirectory (`examples/cpp/`,
`examples/python/`) contains runnable examples for that language, built
against that language's published/local package.

## Shared Metadata: `project.ini`

`project.ini` is the single place where facts that apply to the whole
project — not just one language — are recorded: project name, version,
license, maintainers/contributors, and cross-language compatibility notes
(e.g. minimum C++ standard, minimum Python version).

Both language trees are expected to **read** this file at build/packaging
time rather than hold their own separate copy of these values:

- On the C++ side, `premake5.lua` (or a small helper invoked from it) should
  parse `project.ini` to populate things like the version string.
- On the Python side, `pyproject.toml` can't execute arbitrary parsing
  itself, but a `scripts/` helper (or a `[tool.*]` build backend hook) should
  read `project.ini` and keep `pyproject.toml`'s own `version`/metadata in
  sync, or generate it at build time.

The exact mechanism is left to each language's build scripts; the contract is
just: **`project.ini` is authoritative, and both sides derive from it rather
than duplicating values by hand.**

## Documentation Layout

Shared documentation — things true of the project as a whole, independent of
language — lives directly in `docs/`: this architecture doc, `concepts.md`,
and `semantics.md`. Anything specific to building, testing, or contributing
to one language's implementation lives in that language's own
`docs/<language>/README.md`, keeping the top-level docs free of
implementation details that would otherwise need to be duplicated or kept in
sync across two READMEs.

## CI Layout

Two workflows, matching the two cross-cutting concerns of the repo:

- **`build.yml`** — builds and tests `cpp/` and `python/` as independent
  jobs (so one language failing doesn't block visibility into the other).
- **`documentation.yml`** — validates (and optionally publishes) everything
  under `docs/`.

## Adding Something New

A quick reference for "where does this go":

| You're adding... | It goes in... |
|---|---|
| New C++ library code | `cpp/src/` |
| New Python package code | `python/src/` |
| A dev/build helper script (either language) | `<language>/scripts/` |
| A new CLI tool | `<language>/tool/` |
| A runnable usage example | `examples/<language>/` |
| A concept/behavior shared by both languages | `docs/concepts.md` or `docs/semantics.md` |
| A language-specific build/dev note | `docs/<language>/README.md` |
| A project-wide fact (version, contributor, etc.) | `project.ini` |
