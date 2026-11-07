"""
Hardware discovery and profiling.

@todo Create a threaded object that continuously monitors various hardware metrics such as CPU, GPU, and memory usage.
@todo Create a threaded object that continuously updates the hardware profile with the latest metrics.
"""

from .detector import HardwareDetector, detect_hardware
from .profile import GPUInfo, HardwareProfile

__all__ = ["GPUInfo", "HardwareDetector", "HardwareProfile", "detect_hardware"]