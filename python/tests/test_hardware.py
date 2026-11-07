import json

import pytest

from Hestia.hardware import GPUInfo, HardwareDetector, HardwareProfile
from Hestia.hardware import detector as detector_module
from Hestia.hardware import gpu as gpu_module
from Hestia.hardware import cpu as cpu_module
from Hestia.hardware import memory as memory_module
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

        @classmethod
        def nvmlShutdown(cls):
            cls.stopped = True

    monkeypatch.setattr(gpu_module.importlib, "import_module", lambda _: NVML)
    found = gpu_module._detect_nvidia()
    assert found[0].name == "Test NVIDIA"
    assert found[0].compute_capability == "8.6"
    assert found[0].driver_version == "555.1"
    assert NVML.stopped


def test_amd_probe_parses_memory(monkeypatch):
    class Result:
        returncode = 0
        stdout = json.dumps({"card0": {
            "VRAM Total Memory (B)": str(8 * 1024**3),
            "VRAM Total Used Memory (B)": str(2 * 1024**3),
        }})

    monkeypatch.setattr(gpu_module.subprocess, "run", lambda *args, **kwargs: Result())
    found = gpu_module._detect_amd()
    assert found[0].total_memory_gb == 8.0
    assert found[0].free_memory_gb == 6.0


def test_intel_windows_probe_parses_single_adapter(monkeypatch):
    class Result:
        returncode = 0
        stdout = json.dumps({
            "Name": "Intel Arc",
            "AdapterRAM": 4 * 1024**3,
            "DriverVersion": "31.0",
        })

    monkeypatch.setattr(gpu_module.subprocess, "run", lambda *args, **kwargs: Result())
    found = gpu_module._detect_intel_windows()
    assert found[0].accelerator is AcceleratorType.INTEL_ONEAPI
    assert found[0].total_memory_gb == 4.0
    assert found[0].driver_version == "31.0"


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
    assert found[0].free_memory_gb == 0.0


@pytest.mark.parametrize("value,expected", [("1536 MB", 1.5), ("8 GB", 8.0), ("bad", 0.0)])
def test_apple_memory_parser(value, expected):
    assert gpu_module._parse_memory(value) == expected