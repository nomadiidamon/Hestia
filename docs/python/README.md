# Python Implementation

Build, dev, and contributor notes specific to the Python side of this
project. For cross-language concepts and behavior guarantees, see
[`../concepts.md`](../concepts.md) and [`../semantics.md`](../semantics.md).
For why the repo is laid out this way, see [`../architecture.md`](../architecture.md).

## Layout

```
python/
├── pyproject.toml    # Build/packaging configuration
├── src/               # Package source
├── scripts/           # Dev scripts (build helpers, release, formatting)
└── tool/              # Standalone CLI tool(s)
```

## Requirements

- Python version satisfying `project.ini`'s
  `[compatibility] python_requires`.

## Setting Up a Dev Environment

```bash
cd python
python -m venv .venv
source .venv/bin/activate      # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"        # TODO: define a dev extra in pyproject.toml
```

## Running the Tool

```bash
# TODO: once tool/ has a real entry point, e.g.:
python -m python.tool.<tool_name>
```

## Running Tests

```bash
# TODO: wire up pytest (or chosen test runner)
pytest
```

## Scripts

See `python/scripts/` for developer helper scripts (release automation,
formatting/lint wrappers, local CI reproduction, etc.). Document each script
here as it's added:

| Script | Purpose |
|---|---|
| _`scripts/example.py`_ | _TODO: describe_ |

## Versioning / Metadata

This tree should derive its packaging metadata (name/version/etc.) from the
shared [`../../project.ini`](../../project.ini) rather than hardcoding
duplicate values in `pyproject.toml` — see "Shared Metadata" in
`../architecture.md` for the intended mechanism.
