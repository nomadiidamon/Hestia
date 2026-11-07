"""High-level hardware detection orchestration."""

import logging

from ..types import AcceleratorType
from . import cpu, gpu, memory
from .platform import detect_platform
from .profile import GPUInfo, HardwareProfile

logger = logging.getLogger(__name__)
_ACCELERATOR_PRIORITY = {
    AcceleratorType.NVIDIA_CUDA: 5,
    AcceleratorType.AMD_ROCM: 4,
    AcceleratorType.INTEL_ONEAPI: 3,
    AcceleratorType.APPLE_METAL: 2,
}


class HardwareDetector:
    """Collect a best-effort hardware profile; individual probes may fail."""

    def __init__(self):
        self.profile: HardwareProfile | None = None

    def detect(self) -> HardwareProfile:
        try:
            cpu_info = cpu.detect_cpu()
        except Exception as error:
            logger.debug("CPU detection failed: %s", error)
            cpu_info = {
                "count": 1,
                "physical_cores": 1,
                "logical_cores": 1,
                "frequency_ghz": 0.0,
                "brand": "Unknown",
            }
        ram = memory.detect_memory()
        try:
            detected_gpus = gpu.detect_gpus()
        except Exception as error:
            logger.debug("GPU detection failed: %s", error)
            detected_gpus = []
        try:
            platform_info = detect_platform()
        except Exception as error:
            logger.debug("Platform detection failed: %s", error)
            platform_info = {"name": "Unknown", "version": "Unknown", "python_version": "Unknown"}

        primary = _primary_accelerator(detected_gpus)
        available = max(0.0, float(ram.get("available_gb", 0.0))) * 0.7
        known_free_vram = [
            item.free_memory_gb
            for item in detected_gpus
            if item.accelerator is primary and item.is_available and item.free_memory_gb > 0
        ]
        if known_free_vram:
            available = min(available, min(known_free_vram) * 0.8)

        self.profile = HardwareProfile(
            cpu_count=cpu_info["count"],
            cpu_cores_physical=cpu_info["physical_cores"],
            cpu_cores_logical=cpu_info["logical_cores"],
            cpu_frequency_ghz=cpu_info["frequency_ghz"],
            cpu_brand=cpu_info["brand"],
            ram_total_gb=ram["total_gb"],
            ram_available_gb=ram["available_gb"],
            gpus=list(detected_gpus),
            total_vram_gb=sum(item.total_memory_gb for item in detected_gpus),
            platform_name=platform_info["name"],
            platform_version=platform_info["version"],
            python_version=platform_info["python_version"],
            primary_accelerator=primary,
            available_for_models_gb=available,
        )
        return self.profile

    def get_profile(self) -> HardwareProfile | None:
        return self.profile


def _primary_accelerator(gpus: list[GPUInfo]) -> AcceleratorType:
    if not gpus:
        return AcceleratorType.NONE
    return max(gpus, key=lambda item: _ACCELERATOR_PRIORITY.get(item.accelerator, 0)).accelerator


def detect_hardware() -> HardwareProfile:
    """Detect the current system and return its hardware profile."""
    return HardwareDetector().detect()