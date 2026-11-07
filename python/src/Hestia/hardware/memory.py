"""System memory information discovery."""

import psutil


GIB = 1024**3


def detect_memory() -> dict:
    """Return total and currently available system memory in GiB."""
    try:
        memory = psutil.virtual_memory()
        return {"total_gb": memory.total / GIB, "available_gb": memory.available / GIB}
    except Exception:
        return {"total_gb": 0.0, "available_gb": 0.0}