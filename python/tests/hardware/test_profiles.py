import json
import pytest

from Hestia.hardware import GPUInfo, HardwareDetector, HardwareProfile
from Hestia.hardware import detector as detector_module
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
