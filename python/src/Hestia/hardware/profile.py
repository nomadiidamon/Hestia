"""Typed hardware profile and GPU records."""

from dataclasses import asdict, dataclass, field
from typing import Optional

from ..types import AcceleratorType


@dataclass(frozen=True)
class GPUInfo:
    """Capability information for one detected GPU."""

    index: int
    name: str
    accelerator: AcceleratorType
    total_memory_gb: float
    free_memory_gb: float
    compute_capability: Optional[str] = None
    driver_version: Optional[str] = None
    is_available: bool = True

    def to_dict(self) -> dict:
        data = asdict(self)
        data["accelerator"] = self.accelerator.value
        return data


@dataclass(frozen=True)
class HardwareProfile:
    """Snapshot of CPU, memory, accelerator and platform capabilities."""

    cpu_count: int = 1
    cpu_cores_physical: int = 1
    cpu_cores_logical: int = 1
    cpu_frequency_ghz: float = 0.0
    cpu_brand: str = "Unknown"
    ram_total_gb: float = 0.0
    ram_available_gb: float = 0.0
    gpus: list[GPUInfo] = field(default_factory=list)
    total_vram_gb: float = 0.0
    platform_name: str = "Unknown"
    platform_version: str = "Unknown"
    python_version: str = "Unknown"
    primary_accelerator: AcceleratorType = AcceleratorType.NONE
    available_for_models_gb: float = 0.0

    def to_dict(self) -> dict:
        data = asdict(self)
        data["gpus"] = [gpu.to_dict() for gpu in self.gpus]
        data["primary_accelerator"] = self.primary_accelerator.value
        return data