import ctypes
import json
from types import SimpleNamespace

import pytest

from Hestia.hardware import GPUInfo
from Hestia.hardware import gpu as gpu_module
from Hestia.hardware import _level_zero
from Hestia.types import AcceleratorType


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
