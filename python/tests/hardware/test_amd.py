import ctypes
import json
from types import SimpleNamespace

import pytest

from Hestia.hardware import GPUInfo
from Hestia.hardware import gpu as gpu_module
from Hestia.hardware import _hip
from Hestia.types import AcceleratorType


def test_amd_probe_parses_memory(monkeypatch):
    class Result:
        returncode = 0
        stdout = json.dumps({"card0": {
            "VRAM Total Memory (B)": str(8 * 1024**3),
            "VRAM Total Used Memory (B)": str(2 * 1024**3),
            "PCI Bus": "0000:03:00.0",
        }})

    def run(command, **kwargs):
        assert "--showbus" in command
        return Result()

    monkeypatch.setattr(gpu_module.subprocess, "run", run)
    found = gpu_module._detect_amd()
    assert found[0].total_memory_gb == 8.0
    assert found[0].free_memory_gb == 6.0
    assert found[0].pci_bus_id == "0000:03:00.0"


def test_amd_probe_retries_when_pci_query_is_unsupported(monkeypatch):
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        if "--showbus" in command:
            return SimpleNamespace(returncode=1, stdout="")
        return SimpleNamespace(returncode=0, stdout=json.dumps({
            "card0": {"VRAM Total Memory (B)": str(8 * 1024**3)}
        }))

    monkeypatch.setattr(gpu_module.subprocess, "run", run)
    found = gpu_module._detect_amd()
    assert len(commands) == 2
    assert found[0].total_memory_gb == 8
    assert found[0].pci_bus_id is None


@pytest.mark.parametrize("used,expected", [(None, None), (0, 8), (8 * 1024**3, 0)])
def test_amd_probe_distinguishes_missing_used_memory(monkeypatch, used, expected):
    class Result:
        returncode = 0
        details = {"VRAM Total Memory (B)": str(8 * 1024**3)}
        if used is not None:
            details["VRAM Total Used Memory (B)"] = str(used)
        stdout = json.dumps({"card0": details})

    monkeypatch.setattr(gpu_module.subprocess, "run", lambda *args, **kwargs: Result())
    assert gpu_module._detect_amd()[0].free_memory_gb == expected


def test_amd_uuid_matching_uses_pci_not_device_order():
    gpus = [
        GPUInfo(0, "AMD A", AcceleratorType.AMD_ROCM, 8, 6, pci_bus_id="0000:03:00.0"),
        GPUInfo(1, "AMD B", AcceleratorType.AMD_ROCM, 8, 6, pci_bus_id="04:00.0"),
        GPUInfo(2, "Intel", AcceleratorType.INTEL_ONEAPI, 0, None, pci_bus_id="0000:05:00.0"),
    ]
    devices = [("0000:04:00.0", "uuid-b"), ("0000:03:00.0", "uuid-a")]
    result = gpu_module._attach_gpu_uuids(gpus, devices, AcceleratorType.AMD_ROCM, "HIP")
    assert [item.uuid for item in result] == ["uuid-a", "uuid-b", None]
    assert result[1].pci_bus_id == "0000:04:00.0"


def test_amd_uuid_matching_rejects_ambiguous_pci():
    gpus = [GPUInfo(0, "AMD", AcceleratorType.AMD_ROCM, 0, None, pci_bus_id="04:00.0")]
    devices = [("0000:04:00.0", "uuid-a"), ("0001:04:00.0", "uuid-b")]
    assert gpu_module._attach_gpu_uuids(gpus, devices, AcceleratorType.AMD_ROCM, "HIP") == gpus


def test_amd_integrated_windows_uuid_from_hip(monkeypatch):
    class Result:
        returncode = 0
        stdout = json.dumps({
            "Name": "AMD Radeon Graphics",
            "PNPDeviceID": r"PCI\VEN_1002&DEV_1234\instance",
            "LocationInfo": "PCI bus 3, device 0, function 0",
        })

    monkeypatch.setattr(gpu_module.subprocess, "run", lambda *args, **kwargs: Result())
    monkeypatch.setattr(gpu_module, "_detect_nvidia", lambda: [])
    monkeypatch.setattr(gpu_module, "_detect_amd", lambda: [])
    monkeypatch.setattr(gpu_module, "_detect_intel_windows", lambda: [])
    monkeypatch.setattr(_hip, "amd_device_uuids", lambda system: [("0000:03:00.0", "amd-uuid")])
    found = gpu_module.detect_gpus(system_name="Windows")
    assert len(found) == 1
    assert found[0].uuid == "amd-uuid"
    assert found[0].pci_bus_id == "0000:03:00.0"
    assert found[0].pci_vendor_id == "0x1002"
    assert found[0].pnp_device_id == r"PCI\VEN_1002&DEV_1234\instance"


def test_amd_uuid_discovery_deduplicates_rocm_and_integrated_probes(monkeypatch):
    amd = GPUInfo(0, "AMD GPU 0", AcceleratorType.AMD_ROCM, 8, 6, pci_bus_id="0000:03:00.0")
    integrated = GPUInfo(0, "AMD Radeon", AcceleratorType.AMD_ROCM, 8, None,
                         pci_bus_id="0000:03:00.0", pci_vendor_id="0x1002",
                         pci_device_id="0x1234")
    monkeypatch.setattr(gpu_module, "_detect_nvidia", lambda: [])
    monkeypatch.setattr(gpu_module, "_detect_amd", lambda: [amd])
    monkeypatch.setattr(gpu_module, "_detect_intel_linux", lambda: [])
    monkeypatch.setattr(gpu_module, "_detect_integrated_linux", lambda: [integrated])
    monkeypatch.setattr(_hip, "amd_device_uuids", lambda system: [("0000:03:00.0", "amd-uuid")])
    found = gpu_module.detect_gpus(system_name="Linux")
    assert len(found) == 1
    assert found[0].uuid == "amd-uuid"
    assert found[0].free_memory_gb == 6
    assert found[0].pci_vendor_id == "0x1002"
    assert found[0].pci_device_id == "0x1234"


def test_amd_uuid_deduplication_preserves_distinct_or_unknown_devices():
    gpus = [
        GPUInfo(0, "AMD A", AcceleratorType.AMD_ROCM, 8, 6, pci_bus_id="0000:03:00.0", uuid="a"),
        GPUInfo(1, "AMD B", AcceleratorType.AMD_ROCM, 8, 6, pci_bus_id="0000:03:00.0", uuid="b"),
        GPUInfo(2, "AMD C", AcceleratorType.AMD_ROCM, 8, None, pci_bus_id="0000:03:00.0"),
    ]
    assert gpu_module._merge_amd_uuid_duplicates(gpus) == gpus


def test_hip_enumerates_uuids_and_skips_failed_devices(monkeypatch):
    class Function:
        def __init__(self, implementation):
            self.implementation = implementation

        def __call__(self, *args):
            return self.implementation(*args)

    def device_count(output):
        ctypes.cast(output, ctypes.POINTER(ctypes.c_int)).contents.value = 5
        return 0

    def get_device(output, ordinal):
        if ordinal == 4:
            return 1
        ctypes.cast(output, ctypes.POINTER(ctypes.c_int)).contents.value = ordinal + 10
        return 0

    def get_bus(output, size, ordinal):
        if ordinal == 1:
            return 1
        output.value = f"0000:0{ordinal + 3}:00.0".encode("ascii")
        return 0

    def get_uuid(output, device):
        if device == 12:
            return 1
        identifier = ctypes.cast(output, ctypes.POINTER(_hip._HipUUID)).contents
        if device != 13:
            identifier.bytes[:] = range(16)
        return 0

    library = SimpleNamespace(
        hipGetDeviceCount=Function(device_count),
        hipDeviceGet=Function(get_device),
        hipDeviceGetPCIBusId=Function(get_bus),
        hipDeviceGetUuid=Function(get_uuid),
    )
    monkeypatch.setattr(_hip, "_load_runtime", lambda system: library)
    assert _hip.amd_device_uuids("Linux") == [
        ("0000:03:00.0", "00010203-0405-0607-0809-0a0b0c0d0e0f")
    ]


def test_hip_missing_runtime_and_uuid_api_are_optional(monkeypatch, caplog):
    monkeypatch.setattr(_hip, "_load_runtime", lambda system: None)
    assert _hip.amd_device_uuids("Linux") == []
    monkeypatch.setattr(_hip, "_load_runtime", lambda system: SimpleNamespace())
    with caplog.at_level("DEBUG"):
        assert _hip.amd_device_uuids("Linux") == []
    assert "HIP GPU identification unavailable" in caplog.text
