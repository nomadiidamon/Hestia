"""Operating system and Python runtime information."""

import platform as _platform


def detect_platform() -> dict:
    return {
        "name": _platform.system() or "Unknown",
        "version": _platform.release() or "Unknown",
        "python_version": _platform.python_version(),
    }