"""Best-effort GPU discovery using installed vendor interfaces."""

import importlib
import json
import logging
import platform
import re
import subprocess
from dataclasses import replace
from pathlib import Path

from ..types import AcceleratorType
from . import _hip, _level_zero
from .profile import GPUInfo

logger = logging.getLogger(__name__)
GIB = 1024**3
_WINDOWS_GPU_FIELDS = (
    "Select-Object Name, AdapterRAM, DriverVersion, PNPDeviceID, "
    "@{Name='LocationInfo';Expression={ if ($_.PNPDeviceID -and "
    "(Get-Command Get-PnpDeviceProperty -ErrorAction SilentlyContinue)) { "
    "(Get-PnpDeviceProperty -InstanceId $_.PNPDeviceID "
    "-KeyName 'DEVPKEY_Device_LocationInfo' -ErrorAction SilentlyContinue).Data "
    "} }} | ConvertTo-Json -Compress"
)


def detect_gpus(system_name: str | None = None) -> list[GPUInfo]:
    """Probe all GPU interfaces and return deduplicated list of available devices.
    
    Probes in order: NVIDIA, AMD (dedicated), Intel (dedicated), Apple, then integrated.
    Removes exact duplicates while preserving multiple instances of the same GPU type.
    Reassigns indices sequentially to distinguish multiple GPUs of the same model.
    """
    system_name = system_name or platform.system()
    gpus = []
    
    # Probe dedicated GPUs first
    gpus.extend(_detect_nvidia())
    gpus.extend(_detect_amd())
    if system_name in ("Windows", "Linux"):
        gpus.extend(_detect_intel_windows() if system_name == "Windows" else _detect_intel_linux())
    if system_name == "Darwin":
        gpus.extend(_detect_apple())
    
    # Always probe for integrated graphics (supplements dedicated GPU detection)
    if system_name == "Windows":
        gpus.extend(_detect_integrated_windows())
    elif system_name == "Linux":
        gpus.extend(_detect_integrated_linux())
    
    # Deduplicate exact duplicates while preserving multiple instances of same type
    gpus = _deduplicate_gpus(gpus)
    if any(item.accelerator is AcceleratorType.INTEL_ONEAPI and item.pci_bus_id for item in gpus):
        gpus = _attach_gpu_uuids(gpus, _level_zero.intel_device_uuids(system_name),
                                 AcceleratorType.INTEL_ONEAPI, "Level Zero")
    if any(item.accelerator is AcceleratorType.AMD_ROCM and item.pci_bus_id for item in gpus):
        hip_devices = []
        for address, device_uuid in _hip.amd_device_uuids(system_name):
            normalized = _normalize_pci_bus_id(address)
            if normalized:
                hip_devices.append((normalized, device_uuid))
        gpus = _attach_gpu_uuids(gpus, hip_devices, AcceleratorType.AMD_ROCM, "HIP")
        gpus = _merge_amd_uuid_duplicates(gpus)
    
    return gpus


def _text(value) -> str:
    return value.decode(errors="replace") if isinstance(value, bytes) else str(value)


def _windows_pci_bus_id(location: str | None) -> str | None:
    if not isinstance(location, str):
        return None
    match = re.fullmatch(
        r"PCI (?:segment (\d+) )?bus (\d+), device (\d+), function (\d+)",
        location.strip(), re.IGNORECASE,
    )
    if not match:
        return None
    segment, bus, device, function = match.groups()
    bus, device, function = int(bus), int(device), int(function)
    if bus > 255 or device > 31 or function > 7:
        return None
    address = f"{bus:02x}:{device:02x}.{function:x}"
    if segment is None:
        return address
    segment_number = int(segment)
    return f"{segment_number:04x}:{address}" if segment_number <= 0xFFFFFFFF else None


def _windows_gpu_identifiers(entry: dict) -> dict:
    instance_id = entry.get("PNPDeviceID")
    if not isinstance(instance_id, str) or not instance_id:
        instance_id = None
    match = re.match(r"^PCI\\VEN_([0-9a-f]{4})&DEV_([0-9a-f]{4})(?:&|\\|$)",
                     instance_id or "", re.IGNORECASE)
    bus_id = _windows_pci_bus_id(entry.get("LocationInfo"))
    if match and bus_id is None:
        logger.debug("Windows PCI location unavailable or unrecognized for %s", instance_id)
    return {
        "pnp_device_id": instance_id,
        "pci_bus_id": bus_id,
        "pci_vendor_id": f"0x{match.group(1).lower()}" if match else None,
        "pci_device_id": f"0x{match.group(2).lower()}" if match else None,
    }


def _normalize_pci_bus_id(value: str) -> str | None:
    match = re.fullmatch(r"([0-9a-f]{4,8}):([0-9a-f]{2}):([0-9a-f]{2})\.([0-7])",
                         value.strip(), re.IGNORECASE)
    if not match:
        logger.debug("Unrecognized PCI bus address: %s", value)
        return None
    domain, bus, device, function = (int(part, 16) for part in match.groups())
    if device > 31:
        logger.debug("Invalid PCI device number in bus address: %s", value)
        return None
    return f"{domain:04x}:{bus:02x}:{device:02x}.{function:x}"


def _attach_gpu_uuids(
    gpus: list[GPUInfo], devices: list[tuple[str, str]], accelerator: AcceleratorType, source: str
) -> list[GPUInfo]:
    enriched = []
    for gpu in gpus:
        if gpu.accelerator is not accelerator or not gpu.pci_bus_id or gpu.uuid:
            enriched.append(gpu)
            continue
        address = gpu.pci_bus_id.lower()
        if address.count(":") == 1:
            same_bus = [
                other for other in gpus
                if other.accelerator is accelerator
                and other.pci_bus_id
                and (other.pci_bus_id.lower() == address
                     or other.pci_bus_id.lower().endswith(":" + address))
            ]
            if len(same_bus) != 1:
                logger.debug("Ambiguous detected PCI address %s; skipping UUID", address)
                enriched.append(gpu)
                continue
        matches = [
            (bus_id, device_uuid) for bus_id, device_uuid in devices
            if bus_id == address or (address.count(":") == 1 and bus_id.endswith(":" + address))
        ]
        if len(matches) == 1:
            enriched.append(replace(gpu, pci_bus_id=matches[0][0], uuid=matches[0][1]))
        else:
            if len(matches) > 1:
                logger.debug("Ambiguous %s PCI address %s; skipping UUID", source, address)
            enriched.append(gpu)
    return enriched


def _merge_amd_uuid_duplicates(gpus: list[GPUInfo]) -> list[GPUInfo]:
    merged = []
    seen = {}
    for gpu in gpus:
        key = (gpu.pci_bus_id, gpu.uuid)
        if gpu.accelerator is AcceleratorType.AMD_ROCM and all(key) and key in seen:
            index = seen[key]
            first = merged[index]
            merged[index] = replace(
                first,
                pci_vendor_id=first.pci_vendor_id or gpu.pci_vendor_id,
                pci_device_id=first.pci_device_id or gpu.pci_device_id,
                pnp_device_id=first.pnp_device_id or gpu.pnp_device_id,
                driver_version=first.driver_version or gpu.driver_version,
            )
        else:
            if gpu.accelerator is AcceleratorType.AMD_ROCM and all(key):
                seen[key] = len(merged)
            merged.append(gpu)
    return [replace(gpu, index=index) for index, gpu in enumerate(merged)]


def _deduplicate_gpus(gpus: list[GPUInfo]) -> list[GPUInfo]:
    """Remove exact duplicate GPUs while preserving multiple instances of same model.
    
    Two GPUs are considered exact duplicates if they have identical:
    1. name, accelerator type, total memory, and driver version
    2. AND same PCI bus ID, UUID, and Windows PnP device instance ID
    
    This removes the same GPU detected by multiple probe methods while preserving
    multiple physical instances with different PCI bus IDs or UUIDs.
    """
    if not gpus:
        return []
    
    seen = set()
    deduplicated = []
    
    for gpu in gpus:
        # Create a signature for exact duplicate detection
        # Include PCI bus ID if available to distinguish physical devices
        signature = (
            gpu.name,
            gpu.accelerator,
            round(gpu.total_memory_gb, 2),
            gpu.driver_version or "",
            gpu.pci_bus_id or "",  # Empty string if no PCI info
            gpu.uuid or "",  # Empty string if no UUID
            gpu.pnp_device_id or "",
        )
        
        if signature not in seen:
            # First time seeing this exact GPU - keep it
            seen.add(signature)
            deduplicated.append(gpu)
        else:
            # Exact duplicate from another probe method - skip
            logger.debug("Skipping duplicate GPU: %s (%s, %.1f GB, bus=%s, uuid=%s)", 
                        gpu.name, gpu.accelerator.value, gpu.total_memory_gb, 
                        gpu.pci_bus_id or "unknown", gpu.uuid or "unknown")
    
    # Reassign indices sequentially so all GPUs have clear ordering
    reindexed = [
        GPUInfo(
            index=idx,
            name=gpu.name,
            accelerator=gpu.accelerator,
            total_memory_gb=gpu.total_memory_gb,
            free_memory_gb=gpu.free_memory_gb,
            compute_capability=gpu.compute_capability,
            driver_version=gpu.driver_version,
            is_available=gpu.is_available,
            pci_bus_id=gpu.pci_bus_id,
            uuid=gpu.uuid,
            pci_vendor_id=gpu.pci_vendor_id,
            pci_device_id=gpu.pci_device_id,
            pnp_device_id=gpu.pnp_device_id,
        )
        for idx, gpu in enumerate(deduplicated)
    ]
    
    return reindexed


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
            
            # Extract UUID and PCI info for unique identification
            try:
                uuid = _text(nvml.nvmlDeviceGetUUID(handle))
            except Exception:
                uuid = None
            
            pci_bus_id = None
            pci_vendor_id = None
            pci_device_id = None
            try:
                pci_info = nvml.nvmlDeviceGetPciInfo(handle)
                bus_id = getattr(pci_info, "busId", None)
                if bus_id is not None:
                    pci_bus_id = _normalize_pci_bus_id(_text(bus_id))
                packed_id = getattr(pci_info, "pciDeviceId", None)
                if isinstance(packed_id, int) and 0 < packed_id < 0xFFFFFFFF:
                    vendor_id, device_id = packed_id & 0xFFFF, (packed_id >> 16) & 0xFFFF
                    pci_vendor_id = f"0x{vendor_id:04x}" if vendor_id else None
                    pci_device_id = f"0x{device_id:04x}" if device_id else None
            except Exception as error:
                logger.debug("NVIDIA PCI identification failed: %s", error)
            
            gpus.append(GPUInfo(
                index=index,
                name=_text(nvml.nvmlDeviceGetName(handle)),
                accelerator=AcceleratorType.NVIDIA_CUDA,
                total_memory_gb=memory.total / GIB,
                free_memory_gb=memory.free / GIB,
                compute_capability=capability,
                driver_version=driver,
                uuid=uuid,
                pci_bus_id=pci_bus_id,
                pci_vendor_id=pci_vendor_id,
                pci_device_id=pci_device_id,
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
            ["rocm-smi", "--showmeminfo", "vram", "--showbus", "--json"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0:
            logger.debug("AMD PCI bus query failed; retrying memory-only probe")
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
            used_value = details.get("VRAM Total Used Memory (B)")
            used = int(used_value) if used_value is not None else None
            if total <= 0:
                continue
            gpus.append(GPUInfo(
                index=index,
                name=f"AMD GPU {index}",
                accelerator=AcceleratorType.AMD_ROCM,
                total_memory_gb=total / GIB,
                free_memory_gb=max(0, total - used) / GIB if used is not None else None,
                pci_bus_id=_normalize_pci_bus_id(details["PCI Bus"])
                if isinstance(details.get("PCI Bus"), str) else None,
            ))
        return gpus
    except (OSError, subprocess.SubprocessError, ValueError, TypeError) as error:
        logger.debug("AMD GPU detection failed: %s", error)
        return []


def _detect_intel_windows() -> list[GPUInfo]:
    command = (
        "Get-CimInstance Win32_VideoController | "
        "Where-Object { $_.Name -like '*Intel*' } | "
        + _WINDOWS_GPU_FIELDS
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
                free_memory_gb=None,
                driver_version=entry.get("DriverVersion"),
                **_windows_gpu_identifiers(entry),
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
            
            # Extract PCI device ID and bus info
            device_id = _read_sys_file(card / "device" / "device")
            pci_path = _read_sys_file(card / "device" / "uevent")
            pci_bus_id = None
            if pci_path:
                # Extract PCI_SLOT_NAME from uevent file
                for line in pci_path.split('\n'):
                    if 'PCI_SLOT_NAME' in line:
                        pci_bus_id = line.split('=', 1)[-1]
                        break
            
            gpus.append(GPUInfo(
                index=index,
                name=_read_sys_file(card / "device" / "product_name") or f"Intel GPU {index}",
                accelerator=AcceleratorType.INTEL_ONEAPI,
                total_memory_gb=total_gb,
                free_memory_gb=None,
                driver_version=_read_sys_file(card / "device" / "driver" / "module" / "version"),
                pci_vendor_id=vendor,
                pci_device_id=device_id,
                pci_bus_id=pci_bus_id,
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
                free_memory_gb=None,
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


def _detect_integrated_windows() -> list[GPUInfo]:
    """Detect integrated graphics (AMD Radeon, Intel).
    
    Queries Win32_VideoController for all video adapters not already detected via
    dedicated GPU probes. Extracts memory, driver info, and PCI device ID.
    """
    command = (
        "Get-CimInstance Win32_VideoController | "
        + _WINDOWS_GPU_FIELDS
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
        
        gpus = []
        for index, entry in enumerate(entries):
            name = entry.get("Name", "")
            if not name:
                continue
            
            # Determine accelerator type based on name
            # Skip NVIDIA as it's detected separately via NVML
            name_lower = name.lower()
            if "nvidia" in name_lower or "geforce" in name_lower:
                continue
            elif "amd" in name_lower or "radeon" in name_lower:
                accelerator = AcceleratorType.AMD_ROCM
            elif "intel" in name_lower:
                accelerator = AcceleratorType.INTEL_ONEAPI
            else:
                # Unknown GPU type - skip to avoid false positives
                continue
            
            gpus.append(GPUInfo(
                index=index,
                name=name,
                accelerator=accelerator,
                total_memory_gb=int(entry.get("AdapterRAM") or 0) / GIB,
                free_memory_gb=None,
                driver_version=entry.get("DriverVersion"),
                **_windows_gpu_identifiers(entry),
            ))
        return gpus
    except (OSError, subprocess.SubprocessError, ValueError, TypeError) as error:
        logger.debug("Integrated GPU detection (Windows) failed: %s", error)
        return []


def _detect_integrated_linux() -> list[GPUInfo]:
    """Detect integrated graphics (AMD Radeon, Intel).
    
    Checks /sys/class/drm for devices with AMD (0x1002) or Intel (0x8086) vendor IDs.
    Extracts vendor/device IDs and PCI bus information for unique identification.
    """
    gpus = []
    try:
        drm_path = Path("/sys/class/drm")
        if not drm_path.exists():
            return []
        
        cards = sorted(
            card for card in drm_path.iterdir()
            if card.name.startswith("card") and card.name[4:].isdigit()
        )
        
        for card in cards:
            vendor = _read_sys_file(card / "device" / "vendor")
            if not vendor:
                continue
            
            # Identify vendor and accelerator type
            if vendor == "0x8086":
                accelerator = AcceleratorType.INTEL_ONEAPI
                name_prefix = "Intel"
            elif vendor == "0x1002":
                accelerator = AcceleratorType.AMD_ROCM
                name_prefix = "AMD Radeon"
            else:
                continue
            
            # Try to get product name
            product_name = _read_sys_file(card / "device" / "product_name")
            if not product_name:
                index = len(gpus)
                product_name = f"{name_prefix} GPU {index}"
            
            # Try to get memory info (mainly for Intel)
            memory_bytes = _read_sys_file(card / "device" / "drm" / card.name / "lmem_total_bytes")
            try:
                total_gb = int(memory_bytes or 0) / GIB
            except (ValueError, TypeError):
                total_gb = 0.0
            
            # Extract PCI device ID and bus info
            device_id = _read_sys_file(card / "device" / "device")
            pci_path = _read_sys_file(card / "device" / "uevent")
            pci_bus_id = None
            if pci_path:
                for line in pci_path.split('\n'):
                    if 'PCI_SLOT_NAME' in line:
                        pci_bus_id = line.split('=', 1)[-1]
                        break
            
            index = len(gpus)
            gpus.append(GPUInfo(
                index=index,
                name=product_name,
                accelerator=accelerator,
                total_memory_gb=total_gb,
                free_memory_gb=None,
                driver_version=_read_sys_file(card / "device" / "driver" / "module" / "version"),
                pci_vendor_id=vendor,
                pci_device_id=device_id,
                pci_bus_id=pci_bus_id,
            ))
    except OSError as error:
        logger.debug("Integrated GPU detection (Linux) failed: %s", error)
    
    return gpus