"""Best-effort GPU discovery using installed vendor interfaces."""

import importlib
import json
import logging
import platform
import subprocess
from pathlib import Path

from ..types import AcceleratorType
from .profile import GPUInfo

logger = logging.getLogger(__name__)
GIB = 1024**3


def detect_gpus(system_name: str | None = None) -> list[GPUInfo]:
    """Probe supported GPU interfaces independently; unavailable probes are ignored."""
    system_name = system_name or platform.system()
    gpus = []
    gpus.extend(_detect_nvidia())
    gpus.extend(_detect_amd())
    if system_name in ("Windows", "Linux"):
        gpus.extend(_detect_intel_windows() if system_name == "Windows" else _detect_intel_linux())
    if system_name == "Darwin":
        gpus.extend(_detect_apple())
    return gpus


def _text(value) -> str:
    return value.decode(errors="replace") if isinstance(value, bytes) else str(value)


def _detect_nvidia() -> list[GPUInfo]:
    try:
        nvml = importlib.import_module("pynvml")
    except ImportError:
        return []

    initialized = False
    gpus = []
    try:
        nvml.nvmlInit()
        initialized = True
        driver = _text(nvml.nvmlSystemGetDriverVersion())
        for index in range(nvml.nvmlDeviceGetCount()):
            handle = nvml.nvmlDeviceGetHandleByIndex(index)
            memory = nvml.nvmlDeviceGetMemoryInfo(handle)
            try:
                capability = ".".join(map(str, nvml.nvmlDeviceGetCudaComputeCapability(handle)))
            except Exception:
                capability = None
            gpus.append(GPUInfo(
                index=index,
                name=_text(nvml.nvmlDeviceGetName(handle)),
                accelerator=AcceleratorType.NVIDIA_CUDA,
                total_memory_gb=memory.total / GIB,
                free_memory_gb=memory.free / GIB,
                compute_capability=capability,
                driver_version=driver,
            ))
    except Exception as error:
        logger.debug("NVIDIA GPU detection failed: %s", error)
    finally:
        if initialized:
            try:
                nvml.nvmlShutdown()
            except Exception:
                pass
    return gpus


def _detect_amd() -> list[GPUInfo]:
    try:
        result = subprocess.run(
            ["rocm-smi", "--showmeminfo", "vram", "--json"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0:
            return []
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict):
            return []
        gpus = []
        for index, (_, details) in enumerate(payload.items()):
            if not isinstance(details, dict):
                continue
            total = int(details.get("VRAM Total Memory (B)", 0))
            used = int(details.get("VRAM Total Used Memory (B)", 0))
            if total <= 0:
                continue
            gpus.append(GPUInfo(
                index=index,
                name=f"AMD GPU {index}",
                accelerator=AcceleratorType.AMD_ROCM,
                total_memory_gb=total / GIB,
                free_memory_gb=max(0, total - used) / GIB,
            ))
        return gpus
    except (OSError, subprocess.SubprocessError, ValueError, TypeError) as error:
        logger.debug("AMD GPU detection failed: %s", error)
        return []


def _detect_intel_windows() -> list[GPUInfo]:
    command = (
        "Get-CimInstance Win32_VideoController | "
        "Where-Object { $_.Name -like '*Intel*' } | "
        "Select-Object Name, AdapterRAM, DriverVersion | ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        raw = json.loads(result.stdout)
        entries = raw if isinstance(raw, list) else [raw]
        entries = [entry for entry in entries if isinstance(entry, dict)]
        return [
            GPUInfo(
                index=index,
                name=entry.get("Name", f"Intel GPU {index}"),
                accelerator=AcceleratorType.INTEL_ONEAPI,
                total_memory_gb=int(entry.get("AdapterRAM") or 0) / GIB,
                free_memory_gb=0.0,
                driver_version=entry.get("DriverVersion"),
            )
            for index, entry in enumerate(entries)
        ]
    except (OSError, subprocess.SubprocessError, ValueError, TypeError) as error:
        logger.debug("Intel GPU detection failed: %s", error)
        return []


def _read_sys_file(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip() if path.exists() else None
    except OSError:
        return None


def _detect_intel_linux() -> list[GPUInfo]:
    gpus = []
    try:
        cards = sorted(
            card for card in Path("/sys/class/drm").iterdir()
            if card.name.startswith("card") and card.name[4:].isdigit()
        )
        for card in cards:
            vendor = _read_sys_file(card / "device" / "vendor")
            if vendor != "0x8086":
                continue
            memory_bytes = _read_sys_file(card / "device" / "drm" / card.name / "lmem_total_bytes")
            try:
                total_gb = int(memory_bytes or 0) / GIB
            except ValueError:
                total_gb = 0.0
            index = len(gpus)
            gpus.append(GPUInfo(
                index=index,
                name=_read_sys_file(card / "device" / "product_name") or f"Intel GPU {index}",
                accelerator=AcceleratorType.INTEL_ONEAPI,
                total_memory_gb=total_gb,
                free_memory_gb=0.0,
                driver_version=_read_sys_file(card / "device" / "driver" / "module" / "version"),
            ))
    except OSError as error:
        logger.debug("Intel GPU detection failed: %s", error)
    return gpus


def _detect_apple() -> list[GPUInfo]:
    try:
        result = subprocess.run(
            ["system_profiler", "SPDisplaysDataType", "-json"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            return []
        displays = json.loads(result.stdout).get("SPDisplaysDataType", [])
        if not isinstance(displays, list):
            return []
        displays = [display for display in displays if isinstance(display, dict)]
        gpus = []
        for index, display in enumerate(displays):
            raw_memory = display.get("spdisplays_vram") or display.get("spdisplays_vram_shared", "0 MB")
            total_gb = _parse_memory(raw_memory)
            gpus.append(GPUInfo(
                index=index,
                name=display.get("sppci_model", f"Apple GPU {index}"),
                accelerator=AcceleratorType.APPLE_METAL,
                total_memory_gb=total_gb,
                free_memory_gb=0.0,
                driver_version=display.get("spdisplays_metal"),
            ))
        return gpus
    except (OSError, subprocess.SubprocessError, ValueError, TypeError) as error:
        logger.debug("Apple GPU detection failed: %s", error)
        return []


def _parse_memory(value: str) -> float:
    try:
        amount, unit = value.strip().split(maxsplit=1)
        number = float(amount)
        return number / 1024 if unit.upper().startswith("MB") else number
    except (ValueError, AttributeError):
        return 0.0