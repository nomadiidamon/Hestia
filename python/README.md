# Hestia for Python

Hestia provides system discovery and AI model intelligence. The Python package
exposes hardware profiles and detection, plus a model catalog and advisory
recommendations.

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
import Hestia

info = get_model_info(AcceleratorType.NVIDIA_CUDA, ModelSize.SMALL)
print(info)

profile = Hestia.detect_hardware()
recommendation = Hestia.recommend_model(profile)
Hestia.print_hardware_report(profile, recommendation)
```

Software dependencies can be checked and summarized independently:

```python
from Hestia.software.dependency import DependencyRegistry, SystemCommandDependency
from Hestia.software.doctor import Doctor

registry = DependencyRegistry()
registry.register(SystemCommandDependency("git"))
report = Doctor(registry).run()
print(report.to_dict())
```

Installation is performed only through caller-supplied requests and backends,
with authorization scoped to the approved dependency group and actions. Hestia
does not prompt for approval or infer what to install.

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
