"""
Hardware discovery and profiling.

On macOS, Apple GPU memory is shared with system RAM. The profile includes a
shared-memory amount only when `system_profiler` reports one; otherwise GPU
memory is unknown (0 GB total and unavailable free memory). Metal's recommended
working-set size, GPU families and registry ID are separate fields, not VRAM,
CUDA compute capability or a UUID. They require a unique name match between
Metal and system_profiler. The probe checks Apple families 1-10, Mac families
1-2, Common families 1-3 and Metal families 3-4.
Apple GPUs do not expose PCI/PNP identifiers through this probe, and macOS does
not report a separate graphics driver version here.

@todo Create a threaded object that continuously monitors various hardware metrics such as CPU, GPU, and memory usage.
@todo Create a threaded object that continuously updates the hardware profile with the latest metrics.
"""

from .detector import HardwareDetector, detect_hardware
from .profile import GPUInfo, HardwareProfile

__all__ = ["GPUInfo", "HardwareDetector", "HardwareProfile", "detect_hardware"]