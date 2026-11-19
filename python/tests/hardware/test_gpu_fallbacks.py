import json

from Hestia.hardware import GPUInfo
from Hestia.hardware import gpu as gpu_module
from Hestia.types import AcceleratorType


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
