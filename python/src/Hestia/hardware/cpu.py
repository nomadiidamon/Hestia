"""CPU information discovery."""

import platform
from pathlib import Path

import psutil


def detect_cpu() -> dict:
    """Return CPU counts, current frequency and a best-effort brand string."""
    physical = psutil.cpu_count(logical=False) or 1
    logical = psutil.cpu_count(logical=True) or 1
    try:
        frequency = psutil.cpu_freq()
        frequency_ghz = frequency.current / 1000.0 if frequency else 0.0
    except Exception:
        frequency_ghz = 0.0

    brand = platform.processor().strip() or "Unknown"
    if brand == "Unknown" and platform.system() == "Linux":
        try:
            for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
                if line.lower().startswith(("model name", "hardware")):
                    brand = line.split(":", 1)[1].strip()
                    break
        except (OSError, IndexError):
            pass

    return {
        "count": logical,
        "physical_cores": physical,
        "logical_cores": logical,
        "frequency_ghz": frequency_ghz,
        "brand": brand,
    }