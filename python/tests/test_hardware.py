import ctypes
import json
from types import SimpleNamespace

import pytest

from Hestia.hardware import GPUInfo, HardwareDetector, HardwareProfile
from Hestia.hardware import detector as detector_module
from Hestia.hardware import gpu as gpu_module
from Hestia.hardware import cpu as cpu_module
from Hestia.hardware import memory as memory_module
from Hestia.hardware import _hip, _level_zero
from Hestia.types import AcceleratorType


def test_gpu_and_profile_serialization():
    gpu = GPUInfo(0, "Example", AcceleratorType.NVIDIA_CUDA, 8.0, 6.0)
    profile = HardwareProfile(gpus=[gpu], primary_accelerator=AcceleratorType.NVIDIA_CUDA)

    result = profile.to_dict()
    assert result["gpus"][0]["accelerator"] == "nvidia_cuda"
    assert result["primary_accelerator"] == "nvidia_cuda"
    assert json.loads(json.dumps(result))["gpus"][0]["name"] == "Example"


def test_detector_builds_profile_and_applies_memory_headroom(monkeypatch):
    monkeypatch.setattr(detector_module.cpu, "detect_cpu", lambda: {
        "count": 8, "physical_cores": 4, "logical_cores": 8,
        "frequency_ghz": 3.2, "brand": "CPU",
    })
    monkeypatch.setattr(detector_module.memory, "detect_memory", lambda: {
        "total_gb": 32.0, "available_gb": 20.0,
    })
    monkeypatch.setattr(detector_module.gpu, "detect_gpus", lambda: [
        GPUInfo(0, "GPU", AcceleratorType.NVIDIA_CUDA, 12.0, 10.0),
    ])
    monkeypatch.setattr(detector_module, "detect_platform", lambda: {
        "name": "TestOS", "version": "1", "python_version": "3.10",
    })

    detector = HardwareDetector()
    profile = detector.detect()
    assert detector.get_profile() is profile
    assert profile.cpu_count == 8
    assert profile.total_vram_gb == 12.0
    assert profile.primary_accelerator is AcceleratorType.NVIDIA_CUDA
    assert profile.available_for_models_gb == pytest.approx(8.0)


def test_detector_degrades_when_probes_fail(monkeypatch):
    monkeypatch.setattr(detector_module.cpu, "detect_cpu", lambda: (_ for _ in ()).throw(RuntimeError()))
    monkeypatch.setattr(detector_module.memory, "detect_memory", lambda: {"total_gb": 0, "available_gb": 0})
    monkeypatch.setattr(detector_module.gpu, "detect_gpus", lambda: (_ for _ in ()).throw(RuntimeError()))
    monkeypatch.setattr(detector_module, "detect_platform", lambda: (_ for _ in ()).throw(RuntimeError()))

    profile = HardwareDetector().detect()
    assert profile.cpu_brand == "Unknown"
    assert profile.gpus == []
    assert profile.primary_accelerator is AcceleratorType.NONE
    assert profile.platform_name == "Unknown"
    assert profile.available_for_models_gb == 0.0


def test_primary_accelerator_uses_priority():
    devices = [
        GPUInfo(0, "Intel", AcceleratorType.INTEL_ONEAPI, 8, 0),
        GPUInfo(1, "AMD", AcceleratorType.AMD_ROCM, 8, 4),
        GPUInfo(2, "NVIDIA", AcceleratorType.NVIDIA_CUDA, 8, 4),
    ]
    assert detector_module._primary_accelerator(devices) is AcceleratorType.NVIDIA_CUDA


@pytest.mark.parametrize(
    "devices,primary,available",
    [
        ([], AcceleratorType.NONE, 14.0),
        ([GPUInfo(0, "Busy", AcceleratorType.NVIDIA_CUDA, 8, 0)], AcceleratorType.NVIDIA_CUDA, 0),
        ([GPUInfo(0, "Unknown", AcceleratorType.INTEL_ONEAPI, 0, None)], AcceleratorType.INTEL_ONEAPI, 14.0),
        ([GPUInfo(0, "Unavailable", AcceleratorType.NVIDIA_CUDA, 8, 1, is_available=False)],
         AcceleratorType.NONE, 14.0),
        ([GPUInfo(0, "Unavailable", AcceleratorType.NVIDIA_CUDA, 8, 0, is_available=False),
          GPUInfo(1, "AMD", AcceleratorType.AMD_ROCM, 8, 5)],
         AcceleratorType.AMD_ROCM, 4.0),
        ([GPUInfo(0, "Unknown", AcceleratorType.NVIDIA_CUDA, 8, None),
          GPUInfo(1, "Known", AcceleratorType.NVIDIA_CUDA, 8, 5),
          GPUInfo(2, "Unavailable", AcceleratorType.NVIDIA_CUDA, 8, 0, is_available=False),
          GPUInfo(3, "Other", AcceleratorType.INTEL_ONEAPI, 8, 0)],
         AcceleratorType.NVIDIA_CUDA, 4.0),
        ([GPUInfo(0, "GPU", AcceleratorType.NVIDIA_CUDA, 32, 30)],
         AcceleratorType.NVIDIA_CUDA, 14.0),
        ([GPUInfo(0, "GPU 0", AcceleratorType.NVIDIA_CUDA, 8, 6),
          GPUInfo(1, "GPU 1", AcceleratorType.NVIDIA_CUDA, 8, 2)],
         AcceleratorType.NVIDIA_CUDA, 1.6),
    ],
)
def test_detector_selects_available_gpu_and_caps_known_memory(monkeypatch, devices, primary, available):
    monkeypatch.setattr(detector_module.memory, "detect_memory",
                        lambda: {"total_gb": 32, "available_gb": 20})
    monkeypatch.setattr(detector_module.gpu, "detect_gpus", lambda: devices)
    profile = HardwareDetector().detect()
    assert profile.gpus == devices
    assert profile.total_vram_gb == sum(device.total_memory_gb for device in devices)
    assert profile.primary_accelerator is primary
    assert profile.available_for_models_gb == pytest.approx(available)


def test_detector_does_not_report_negative_model_memory(monkeypatch):
    monkeypatch.setattr(detector_module.memory, "detect_memory",
                        lambda: {"total_gb": 8, "available_gb": -1})
    monkeypatch.setattr(detector_module.gpu, "detect_gpus", lambda: [])
    assert HardwareDetector().detect().available_for_models_gb == 0


def test_gpu_serialization_preserves_unknown_memory_and_identifiers():
    gpu = GPUInfo(0, "GPU", AcceleratorType.INTEL_ONEAPI, 0, None,
                  pci_bus_id="0000:01:00.0", uuid="gpu-id",
                  pci_vendor_id="0x8086", pci_device_id="0x1234", pnp_device_id="pnp-id")
    data = json.loads(json.dumps(HardwareProfile(gpus=[gpu]).to_dict()))["gpus"][0]
    assert data["free_memory_gb"] is None
    assert (data["pci_bus_id"], data["uuid"], data["pci_vendor_id"], data["pci_device_id"]) == (
        "0000:01:00.0", "gpu-id", "0x8086", "0x1234",
    )
    assert data["pnp_device_id"] == "pnp-id"


def test_nvidia_probe_is_optional(monkeypatch):
    monkeypatch.setattr(gpu_module.importlib, "import_module", lambda _: (_ for _ in ()).throw(ImportError()))
    assert gpu_module._detect_nvidia() == []


def test_cpu_probe_reports_counts_frequency_and_brand(monkeypatch):
    monkeypatch.setattr(cpu_module.psutil, "cpu_count", lambda logical: 8 if logical else 4)
    monkeypatch.setattr(cpu_module.psutil, "cpu_freq", lambda: type("Frequency", (), {"current": 3200})())
    monkeypatch.setattr(cpu_module.platform, "processor", lambda: "Test CPU")
    result = cpu_module.detect_cpu()
    assert result == {
        "count": 8,
        "physical_cores": 4,
        "logical_cores": 8,
        "frequency_ghz": 3.2,
        "brand": "Test CPU",
    }


def test_memory_probe_converts_bytes_and_degrades(monkeypatch):
    monkeypatch.setattr(memory_module.psutil, "virtual_memory", lambda: type(
        "Memory", (), {"total": 8 * 1024**3, "available": 3 * 1024**3}
    )())
    assert memory_module.detect_memory() == {"total_gb": 8.0, "available_gb": 3.0}
    monkeypatch.setattr(memory_module.psutil, "virtual_memory", lambda: (_ for _ in ()).throw(OSError()))
    assert memory_module.detect_memory() == {"total_gb": 0.0, "available_gb": 0.0}


def test_nvidia_probe_parses_device_and_always_shuts_down(monkeypatch):
    class NVML:
        stopped = False

        @staticmethod
        def nvmlInit():
            pass

        @staticmethod
        def nvmlSystemGetDriverVersion():
            return b"555.1"

        @staticmethod
        def nvmlDeviceGetCount():
            return 1

        @staticmethod
        def nvmlDeviceGetHandleByIndex(index):
            return index

        @staticmethod
        def nvmlDeviceGetMemoryInfo(handle):
            return type("Memory", (), {"total": 8 * 1024**3, "free": 6 * 1024**3})()

        @staticmethod
        def nvmlDeviceGetCudaComputeCapability(handle):
            return (8, 6)

        @staticmethod
        def nvmlDeviceGetName(handle):
            return b"Test NVIDIA"

        @staticmethod
        def nvmlDeviceGetUUID(handle):
            return b"GPU-example"

        @staticmethod
        def nvmlDeviceGetPciInfo(handle):
            return type("PCI", (), {"busId": b"00000000:02:00.0", "pciDeviceId": 0x2D5810DE})()

        @classmethod
        def nvmlShutdown(cls):
            cls.stopped = True

    monkeypatch.setattr(gpu_module.importlib, "import_module", lambda _: NVML)
    found = gpu_module._detect_nvidia()
    assert found[0].name == "Test NVIDIA"
    assert found[0].compute_capability == "8.6"
    assert found[0].driver_version == "555.1"
    assert found[0].uuid == "GPU-example"
    assert found[0].pci_bus_id == "0000:02:00.0"
    assert found[0].pci_vendor_id == "0x10de"
    assert found[0].pci_device_id == "0x2d58"
    assert NVML.stopped


@pytest.mark.parametrize(
    "pci_info,bus_id,vendor_id,device_id",
    [
        (SimpleNamespace(busId=b"00000000:02:00.0"), "0000:02:00.0", None, None),
        (SimpleNamespace(pciDeviceId=0x2D5810DE), None, "0x10de", "0x2d58"),
        (SimpleNamespace(busId=b"invalid", pciDeviceId=0xFFFFFFFF), None, None, None),
    ],
)
def test_nvidia_probe_keeps_available_partial_pci_info(monkeypatch, pci_info, bus_id, vendor_id, device_id):
    nvml = SimpleNamespace(
        nvmlInit=lambda: None,
        nvmlShutdown=lambda: None,
        nvmlSystemGetDriverVersion=lambda: "test",
        nvmlDeviceGetCount=lambda: 1,
        nvmlDeviceGetHandleByIndex=lambda index: index,
        nvmlDeviceGetMemoryInfo=lambda handle: SimpleNamespace(total=8 * 1024**3, free=0),
        nvmlDeviceGetCudaComputeCapability=lambda handle: (8, 6),
        nvmlDeviceGetUUID=lambda handle: "GPU-example",
        nvmlDeviceGetPciInfo=lambda handle: pci_info,
        nvmlDeviceGetName=lambda handle: "Test NVIDIA",
    )
    monkeypatch.setattr(gpu_module.importlib, "import_module", lambda _: nvml)
    found = gpu_module._detect_nvidia()[0]
    assert (found.pci_bus_id, found.pci_vendor_id, found.pci_device_id) == (bus_id, vendor_id, device_id)


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


def test_intel_windows_probe_parses_single_adapter(monkeypatch):
    class Result:
        returncode = 0
        stdout = json.dumps({
            "Name": "Intel Arc",
            "AdapterRAM": 4 * 1024**3,
            "DriverVersion": "31.0",
            "PNPDeviceID": r"PCI\VEN_8086&DEV_7D67&SUBSYS_12345678\instance",
            "LocationInfo": "PCI bus 0, device 2, function 0",
        })

    monkeypatch.setattr(gpu_module.subprocess, "run", lambda *args, **kwargs: Result())
    found = gpu_module._detect_intel_windows()
    assert found[0].accelerator is AcceleratorType.INTEL_ONEAPI
    assert found[0].total_memory_gb == 4.0
    assert found[0].free_memory_gb is None
    assert found[0].driver_version == "31.0"
    assert found[0].pci_vendor_id == "0x8086"
    assert found[0].pci_device_id == "0x7d67"
    assert found[0].pci_bus_id == "00:02.0"
    assert found[0].pnp_device_id == r"PCI\VEN_8086&DEV_7D67&SUBSYS_12345678\instance"
    assert found[0].uuid is None


@pytest.mark.parametrize(
    "location,expected",
    [
        ("PCI bus 2, device 0, function 0", "02:00.0"),
        ("PCI segment 12 bus 13, device 14, function 3", "000c:0d:0e.3"),
        ("PCI bus 256, device 0, function 0", None),
        ("PCI bus 0, device 32, function 0", None),
        ("PCI bus 0, device 0, function 8", None),
        ("unknown", None),
        (None, None),
    ],
)
def test_windows_pci_location(location, expected):
    assert gpu_module._windows_pci_bus_id(location) == expected


def test_windows_pnp_ids_distinguish_gpus_without_bus_addresses(monkeypatch):
    class Result:
        returncode = 0
        stdout = json.dumps([
            {"Name": "Intel Graphics", "PNPDeviceID": r"PCI\VEN_8086&DEV_7D67\first"},
            {"Name": "Intel Graphics", "PNPDeviceID": r"PCI\VEN_8086&DEV_7D67\second"},
        ])

    monkeypatch.setattr(gpu_module.subprocess, "run", lambda *args, **kwargs: Result())
    monkeypatch.setattr(gpu_module, "_detect_nvidia", lambda: [])
    monkeypatch.setattr(gpu_module, "_detect_amd", lambda: [])
    found = gpu_module.detect_gpus(system_name="Windows")
    assert len(found) == 2
    assert [item.pci_bus_id for item in found] == [None, None]
    assert [item.pnp_device_id for item in found] == [
        r"PCI\VEN_8086&DEV_7D67\first", r"PCI\VEN_8086&DEV_7D67\second"
    ]
    assert all(item.pci_vendor_id == "0x8086" and item.pci_device_id == "0x7d67" for item in found)


@pytest.mark.parametrize("instance_id", [None, "", r"USB\VEN_8086&DEV_7D67\instance",
                                         r"PCI\VEN_808&DEV_7D67\instance"])
def test_windows_pnp_id_does_not_invent_pci_identifiers(instance_id):
    identifiers = gpu_module._windows_gpu_identifiers({"PNPDeviceID": instance_id})
    assert identifiers["pci_vendor_id"] is None
    assert identifiers["pci_device_id"] is None
    assert identifiers["pci_bus_id"] is None


@pytest.mark.parametrize(
    "gpu_address,devices,expected",
    [
        ("00:02.0", [("0000:00:02.0", "uuid-1")], ("0000:00:02.0", "uuid-1")),
        ("0001:00:02.0", [("0001:00:02.0", "uuid-2")], ("0001:00:02.0", "uuid-2")),
        ("0001:00:02.0", [("0000:00:02.0", "uuid-1")], ("0001:00:02.0", None)),
        ("00:02.0", [("0000:00:02.0", "uuid-1"), ("0001:00:02.0", "uuid-2")],
         ("00:02.0", None)),
        ("00:02.0", [], ("00:02.0", None)),
    ],
)
def test_attach_intel_uuid_matches_unambiguous_pci_address(gpu_address, devices, expected):
    gpu = GPUInfo(0, "Intel", AcceleratorType.INTEL_ONEAPI, 0, None, pci_bus_id=gpu_address)
    result = gpu_module._attach_gpu_uuids([gpu], devices, AcceleratorType.INTEL_ONEAPI, "Level Zero")[0]
    assert (result.pci_bus_id, result.uuid) == expected


def test_attach_intel_uuid_rejects_ambiguous_detected_devices():
    gpus = [
        GPUInfo(0, "Intel A", AcceleratorType.INTEL_ONEAPI, 0, None, pci_bus_id="00:02.0"),
        GPUInfo(1, "Intel B", AcceleratorType.INTEL_ONEAPI, 0, None, pci_bus_id="00:02.0"),
    ]
    result = gpu_module._attach_gpu_uuids(gpus, [("0000:00:02.0", "uuid-1")],
                                          AcceleratorType.INTEL_ONEAPI, "Level Zero")
    assert [item.uuid for item in result] == [None, None]


def test_attach_intel_uuid_preserves_other_and_existing_uuids():
    gpus = [
        GPUInfo(0, "Intel", AcceleratorType.INTEL_ONEAPI, 0, None,
                pci_bus_id="00:02.0", uuid="existing"),
        GPUInfo(1, "NVIDIA", AcceleratorType.NVIDIA_CUDA, 8, 6, pci_bus_id="00:02.0"),
    ]
    assert gpu_module._attach_gpu_uuids(gpus, [("0000:00:02.0", "uuid-1")],
                                        AcceleratorType.INTEL_ONEAPI, "Level Zero") == gpus


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


def test_detect_gpus_enriches_intel_after_deduplication(monkeypatch):
    class Result:
        returncode = 0
        stdout = json.dumps({
            "Name": "Intel Graphics",
            "PNPDeviceID": r"PCI\VEN_8086&DEV_7D67\instance",
            "LocationInfo": "PCI bus 0, device 2, function 0",
        })

    monkeypatch.setattr(gpu_module.subprocess, "run", lambda *args, **kwargs: Result())
    monkeypatch.setattr(gpu_module, "_detect_nvidia", lambda: [])
    monkeypatch.setattr(gpu_module, "_detect_amd", lambda: [])
    monkeypatch.setattr(_level_zero, "intel_device_uuids",
                        lambda system: [("0000:00:02.0", "intel-uuid")])
    found = gpu_module.detect_gpus(system_name="Windows")
    assert len(found) == 1
    assert found[0].uuid == "intel-uuid"
    assert found[0].pci_bus_id == "0000:00:02.0"
    assert found[0].pnp_device_id == r"PCI\VEN_8086&DEV_7D67\instance"


def test_level_zero_enumerates_and_filters_intel_devices(monkeypatch):
    class Function:
        def __init__(self, name, implementation):
            self.__name__ = name
            self.implementation = implementation

        def __call__(self, *args):
            return self.implementation(*args)

    def handles(count_ptr, result, values):
        ctypes.cast(count_ptr, ctypes.POINTER(ctypes.c_uint32)).contents.value = len(values)
        if result is not None:
            for index, value in enumerate(values):
                result[index] = value
        return 0

    def device_properties(device, output):
        if device == 6:
            return 1
        properties = ctypes.cast(output, ctypes.POINTER(_level_zero._DeviceProperties)).contents
        properties.type = 1
        properties.vendorId = 0x10DE if device == 3 else 0x8086
        if device != 4:
            properties.uuid[:] = range(16)
        return 0

    def pci_properties(device, output):
        if device == 5:
            return 1
        pci = ctypes.cast(output, ctypes.POINTER(_level_zero._PciProperties)).contents
        pci.address.bus = 3
        pci.address.device = 2
        return 0

    library = SimpleNamespace(
        zeInit=Function("zeInit", lambda flags: 0),
        zeDriverGet=Function("zeDriverGet", lambda count, result: handles(count, result, [1])),
        zeDeviceGet=Function("zeDeviceGet", lambda driver, count, result: handles(count, result, [2, 3, 4, 5, 6])),
        zeDeviceGetProperties=Function("zeDeviceGetProperties", device_properties),
        zeDevicePciGetPropertiesExt=Function("zeDevicePciGetPropertiesExt", pci_properties),
    )
    monkeypatch.setattr(_level_zero.ctypes, "CDLL", lambda name: library)
    assert _level_zero.intel_device_uuids("Linux") == [
        ("0000:03:02.0", "00010203-0405-0607-0809-0a0b0c0d0e0f")
    ]


def test_level_zero_missing_runtime_is_optional(monkeypatch, caplog):
    def missing_loader(name):
        raise OSError("loader unavailable")

    monkeypatch.setattr(_level_zero.ctypes, "CDLL", missing_loader)
    with caplog.at_level("DEBUG"):
        assert _level_zero.intel_device_uuids("Linux") == []
    assert "loader unavailable" in caplog.text


def test_apple_probe_parses_shared_memory(monkeypatch):
    class Result:
        returncode = 0
        stdout = json.dumps({"SPDisplaysDataType": [{
            "sppci_model": "Apple GPU",
            "spdisplays_vram_shared": "8192 MB",
            "spdisplays_metal": "Metal 3",
        }]})

    monkeypatch.setattr(gpu_module.subprocess, "run", lambda *args, **kwargs: Result())
    found = gpu_module._detect_apple()
    assert found[0].accelerator is AcceleratorType.APPLE_METAL
    assert found[0].total_memory_gb == 8.0
    assert found[0].free_memory_gb is None


@pytest.mark.parametrize("value,expected", [("1536 MB", 1.5), ("8 GB", 8.0), ("bad", 0.0)])
def test_apple_memory_parser(value, expected):
    assert gpu_module._parse_memory(value) == expected


def test_integrated_gpu_fallback_windows(monkeypatch):
    """Test that integrated graphics are detected when no dedicated GPUs found."""
    class Result:
        returncode = 0
        stdout = json.dumps([
            {
                "Name": "AMD Radeon Graphics",
                "AdapterRAM": 2 * 1024**3,
                "DriverVersion": "24.10",
            },
        ])

    monkeypatch.setattr(gpu_module.subprocess, "run", lambda *args, **kwargs: Result())
    monkeypatch.setattr(gpu_module, "_detect_nvidia", lambda: [])
    monkeypatch.setattr(gpu_module, "_detect_amd", lambda: [])
    monkeypatch.setattr(gpu_module, "_detect_intel_windows", lambda: [])
    
    found = gpu_module.detect_gpus(system_name="Windows")
    assert len(found) == 1
    assert found[0].accelerator is AcceleratorType.AMD_ROCM
    assert found[0].name == "AMD Radeon Graphics"
    assert found[0].total_memory_gb == 2.0
    assert found[0].free_memory_gb is None


def test_integrated_linux_fallback_and_duplicate_intel_probe(monkeypatch, tmp_path):
    card = tmp_path / "card0" / "device"
    card.mkdir(parents=True)
    (card / "vendor").write_text("0x8086", encoding="utf-8")
    (card / "device").write_text("0x1234", encoding="utf-8")
    (card / "uevent").write_text("PCI_SLOT_NAME=0000:00:02.0\n", encoding="utf-8")
    monkeypatch.setattr(gpu_module, "Path", lambda path: tmp_path)
    monkeypatch.setattr(gpu_module, "_detect_nvidia", lambda: [])
    monkeypatch.setattr(gpu_module, "_detect_amd", lambda: [])

    found = gpu_module.detect_gpus(system_name="Linux")
    assert len(found) == 1
    assert found[0].accelerator is AcceleratorType.INTEL_ONEAPI
    assert found[0].free_memory_gb is None
    assert found[0].pci_bus_id == "0000:00:02.0"
    assert found[0].pci_vendor_id == "0x8086"
    assert found[0].pci_device_id == "0x1234"


def test_mixed_dedicated_and_integrated_gpus(monkeypatch):
    """Test that both dedicated and integrated GPUs are found together."""
    # Dedicated NVIDIA GPU
    nvidia_gpu = GPUInfo(0, "NVIDIA RTX 5070", AcceleratorType.NVIDIA_CUDA, 8.0, 7.5,
                        driver_version="592.07", pci_bus_id="0000:02:00.0",
                        uuid="GPU-72f5f8c1-5c9e-a693-fe89-9fc1b25048e9",
                        pci_vendor_id="0x10de", pci_device_id="0x2cb8")
    
    monkeypatch.setattr(gpu_module, "_detect_nvidia", lambda: [nvidia_gpu])
    monkeypatch.setattr(gpu_module, "_detect_amd", lambda: [])
    
    # Integrated Intel GPU
    class IntegratedResult:
        returncode = 0
        stdout = json.dumps({
            "Name": "Intel Arc",
            "AdapterRAM": 2 * 1024**3,
            "DriverVersion": "32.0.101.8860",
        })
    
    monkeypatch.setattr(gpu_module.subprocess, "run", lambda *args, **kwargs: IntegratedResult())
    monkeypatch.setattr(gpu_module, "_detect_intel_windows", lambda: [])
    
    found = gpu_module.detect_gpus(system_name="Windows")
    
    # Should find BOTH GPUs (not just fallback to integrated)
    assert len(found) == 2
    assert found[0].name == "NVIDIA RTX 5070"
    assert found[0].accelerator is AcceleratorType.NVIDIA_CUDA
    assert found[0].uuid == "GPU-72f5f8c1-5c9e-a693-fe89-9fc1b25048e9"
    
    assert found[1].name == "Intel Arc"
    assert found[1].accelerator is AcceleratorType.INTEL_ONEAPI


def test_multiple_identical_gpus_preserved(monkeypatch):
    """Test that multiple identical GPUs are preserved using hardware identifiers."""
    # Two RTX 3050s with different UUIDs and PCI bus IDs
    gpu_0 = GPUInfo(0, "NVIDIA RTX 3050", AcceleratorType.NVIDIA_CUDA, 8.0, 7.2,
                   driver_version="555.42", pci_bus_id="0000:0A:00.0",
                   uuid="GPU-a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
                   pci_vendor_id="0x10de", pci_device_id="0x2505")
    
    gpu_1 = GPUInfo(1, "NVIDIA RTX 3050", AcceleratorType.NVIDIA_CUDA, 8.0, 6.8,
                   driver_version="555.42", pci_bus_id="0000:11:00.0",
                   uuid="GPU-f5e6d7c8-b9a0-4d1e-2f3a-4b5c6d7e8f9a",
                   pci_vendor_id="0x10de", pci_device_id="0x2505")
    
    monkeypatch.setattr(gpu_module, "_detect_nvidia", lambda: [gpu_0, gpu_1])
    monkeypatch.setattr(gpu_module, "_detect_amd", lambda: [])
    
    class FakeResult:
        returncode = 0
        stdout = json.dumps([])
    
    monkeypatch.setattr(gpu_module.subprocess, "run", lambda *args, **kwargs: FakeResult())
    monkeypatch.setattr(gpu_module, "_detect_intel_windows", lambda: [])
    
    found = gpu_module.detect_gpus(system_name="Windows")
    
    # Both GPUs should be preserved (not deduplicated)
    assert len(found) == 2
    
    # Check GPU 0
    assert found[0].name == "NVIDIA RTX 3050"
    assert found[0].index == 0
    assert found[0].pci_bus_id == "0000:0A:00.0"
    assert found[0].uuid == "GPU-a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
    
    # Check GPU 1
    assert found[1].name == "NVIDIA RTX 3050"
    assert found[1].index == 1
    assert found[1].pci_bus_id == "0000:11:00.0"
    assert found[1].uuid == "GPU-f5e6d7c8-b9a0-4d1e-2f3a-4b5c6d7e8f9a"
    
    # Both have same device ID (same chip model) but different UUIDs
    assert found[0].pci_device_id == found[1].pci_device_id
    assert found[0].uuid != found[1].uuid