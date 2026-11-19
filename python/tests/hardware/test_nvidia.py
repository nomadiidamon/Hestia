from types import SimpleNamespace

import pytest

from Hestia.hardware import gpu as gpu_module


def test_nvidia_probe_is_optional(monkeypatch):
    monkeypatch.setattr(gpu_module.importlib, "import_module", lambda _: (_ for _ in ()).throw(ImportError()))
    assert gpu_module._detect_nvidia() == []


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
