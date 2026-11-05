# Python Implementation

Build, dev, and contributor notes specific to the Python side of this
project. For cross-language concepts and behavior guarantees, see
[`../Concepts.md`](../Concepts.md) and [`../Semantics.md`](../Semantics.md).
For why the repo is laid out this way, see [`../Architecture.md`](../Architecture.md).

Distribution name: `hestia-system`. Import name: `Hestia`.

## Status

Implemented: `Hestia.types` and the `Hestia.models` subpackage (catalog,
`ModelInfo`, `get_model_info()`), plus the legacy `Hestia.model_catalog` path.
Planned: `hardware`, `software`, the recommender and the `hestia` CLI.

## Layout

```
python/
+-- pyproject.toml     # Static packaging configuration
+-- setup.py           # Reads metadata from ../project.ini
+-- src/Hestia/        # Package source
|   +-- types.py
|   +-- model_catalog.py   # Legacy path
|   `-- models/
+-- tests/             # pytest suite
+-- scripts/           # clean / run_tests wrappers (.bat and .sh)
`-- tools/             # clean.py, run_tests.py and per-sub-package tools
    `-- models/
```

## Requirements

- Python version satisfying `project.ini`'s `[compatibility] python_requires`
  (currently 3.10 or later).
- Runtime dependency: `psutil`.
- Optional extras: `nvidia` (`nvidia-ml-py`), `dev` (`pytest`).

## Setting Up a Dev Environment

```bash
cd python
python -m venv .venv
source .venv/bin/activate      # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

The build reads `../project.ini`, so install from a full repository checkout.

## Usage

```python
import Hestia
from Hestia import AcceleratorType, ModelSize

info = Hestia.get_model_info(AcceleratorType.NVIDIA_CUDA, ModelSize.SMALL)
print(info.get("tools"))
```

Runnable examples are in `examples/python/models/`.

## Running Tests

```bash
cd python
pytest
```

or use `scripts/run_tests.bat` / `scripts/run_tests.sh`. `tools/run_tests.py`
delegates to each `tools/<subpackage>/run_tests.py` and collects output in
`tests/test_output.txt`. `tests/test_examples.py` runs every script under
`examples/python/`.

## Scripts and Tools

| Item | Purpose |
|---|---|
| `scripts/run_tests.bat`, `.sh` | Run the test suite through `tools/run_tests.py`. |
| `scripts/clean.bat`, `.sh` | Run `tools/clean.py`. |
| `tools/run_tests.py` | Runs each sub-package's `run_tests.py`. |
| `tools/clean.py` | Uninstalls the package, runs each sub-package's `clean.py`, then removes `build`, `dist`, caches, `egg-info` and `__pycache__`. Supports `--dry-run` and `-y`. |
| `tools/models/run_tests.py` | Runs the models tests and the examples test. |
| `tools/models/clean.py` | Cleans models-related artifacts. |

To add a sub-package, create `tools/<name>/clean.py` (picked up
automatically by `clean.py`) and add the name to `SUITES` in
`tools/run_tests.py`.

## Versioning / Metadata

Name, version, description, license, authors, homepage and `requires-python`
come from [`../../project.ini`](../../project.ini) through `setup.py`; do not
hardcode them in `pyproject.toml`. The pre-commit hook checks the version
against the Doxyfile `PROJECT_NUMBER`.
