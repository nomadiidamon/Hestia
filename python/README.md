# Hestia for Python

Hestia provides system discovery and AI model intelligence. The Python package
currently exposes accelerator and model-size types, a model catalog, and model
information lookup.

The distribution is named `hestia-system`; import it as `Hestia`.

## Installation

```bash
python -m pip install hestia-system
```

Optional dependencies are available as extras:

```bash
python -m pip install "hestia-system[nvidia]"  # NVIDIA telemetry support
python -m pip install "hestia-system[dev]"     # pytest
```

## Usage

```python
from Hestia import AcceleratorType, ModelSize, get_model_info

info = get_model_info(AcceleratorType.NVIDIA_CUDA, ModelSize.SMALL)
print(info)
```

The package supports Python versions declared by the project metadata (Python
3.10 and later).

## Development

From the repository checkout:

```bash
cd python
python -m pip install -e ".[dev]"
python -m pytest
```

Package metadata is maintained in the repository's `project.ini`. Source
distributions include a copy of that file so they can be built independently
of the repository checkout.
