import ctypes
import json
from types import SimpleNamespace

import pytest

from Hestia.hardware import GPUInfo, HardwareDetector, HardwareProfile
from Hestia.hardware import detector as detector_module
from Hestia.hardware import gpu as gpu_module
from Hestia.hardware import _metal
from Hestia.types import AcceleratorType


def test_apple_probe_parses_shared_memory(monkeypatch):
    class Result:
        returncode = 0
        stdout = json.dumps({"SPDisplaysDataType": [{
            "sppci_model": "Apple GPU",
            "spdisplays_vram_shared": "8192 MB",
            "spdisplays_metal": "Metal 3",
        }]})

    monkeypatch.setattr(gpu_module.subprocess, "run", lambda *args, **kwargs: Result())
    monkeypatch.setattr(_metal, "metal_devices", lambda: [])
    found = gpu_module._detect_apple()
    assert found[0].accelerator is AcceleratorType.APPLE_METAL
    assert found[0].total_memory_gb == 8.0
    assert found[0].free_memory_gb is None
    assert found[0].compute_capability is None
    assert found[0].driver_version is None
    assert found[0].pci_bus_id is None
    assert found[0].uuid is None
    assert found[0].pci_vendor_id is None
    assert found[0].pci_device_id is None
    assert found[0].pnp_device_id is None


def test_apple_probe_attaches_metal_details_by_unique_name(monkeypatch):
    displays = [
        {"sppci_model": "Apple M1"},
        {"sppci_model": "External GPU", "spdisplays_vram": "8 GB"},
    ]
    monkeypatch.setattr(gpu_module.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=0, stdout=json.dumps({"SPDisplaysDataType": displays}),
    ))
    monkeypatch.setattr(_metal, "metal_devices", lambda: [
        _metal.MetalDevice("External GPU", 4, ["Mac 2"], 99),
        _metal.MetalDevice("Apple M1", 10.5, ["Apple 7", "Mac 2"], 42),
    ])
    monkeypatch.setattr(gpu_module, "_detect_nvidia", lambda: [])
    monkeypatch.setattr(gpu_module, "_detect_amd", lambda: [])

    found = gpu_module.detect_gpus(system_name="Darwin")
    assert found[0].total_memory_gb == 0
    assert found[0].free_memory_gb is None
    assert found[0].compute_capability is None
    assert found[0].uuid is None
    assert found[0].metal_recommended_working_set_gb == 10.5
    assert found[0].metal_gpu_families == ["Apple 7", "Mac 2"]
    assert found[0].metal_registry_id == 42
    assert found[1].metal_registry_id == 99
    data = json.loads(json.dumps(HardwareProfile(gpus=found).to_dict()))["gpus"][0]
    assert data["metal_recommended_working_set_gb"] == 10.5
    assert data["metal_gpu_families"] == ["Apple 7", "Mac 2"]
    assert data["metal_registry_id"] == 42


def test_metal_working_set_does_not_change_model_memory(monkeypatch):
    gpu = GPUInfo(0, "Apple M1", AcceleratorType.APPLE_METAL, 0, None,
                  metal_recommended_working_set_gb=2)
    monkeypatch.setattr(detector_module.memory, "detect_memory",
                        lambda: {"total_gb": 16, "available_gb": 10})
    monkeypatch.setattr(detector_module.gpu, "detect_gpus", lambda: [gpu])
    assert HardwareDetector().detect().available_for_models_gb == pytest.approx(7)


@pytest.mark.parametrize("names,metal_names", [
    (["Same", "Same"], ["Same"]),
    (["Same"], ["Same", "Same"]),
    (["Same"], ["Other"]),
])
def test_metal_details_require_unambiguous_name_match(names, metal_names):
    gpus = [GPUInfo(i, name, AcceleratorType.APPLE_METAL, 0, None)
            for i, name in enumerate(names)]
    devices = [_metal.MetalDevice(name, 5, ["Apple 7"], i)
               for i, name in enumerate(metal_names)]
    result = gpu_module._attach_metal_details(gpus, devices)
    assert result == gpus


def test_metal_probe_reads_available_properties_and_releases_objects(monkeypatch):
    class FakeAPI:
        objc = SimpleNamespace(objc_getClass=lambda name: 1)
        metal = SimpleNamespace(MTLCopyAllDevices=lambda: 3)

        def __init__(self):
            self.released = []

        def pointer(self, obj, name):
            return {(1, "alloc"): 2, (2, "init"): 4, (5, "name"): 6}[(obj, name)]

        def integer(self, obj, name):
            return {(3, "count"): 1, (5, "recommendedMaxWorkingSetSize"): 8 * 1024**3,
                    (5, "registryID"): 42}[(obj, name)]

        def indexed(self, obj, index):
            assert (obj, index) == (3, 0)
            return 5

        def string(self, obj):
            assert obj == 6
            return b"Apple M1"

        def responds(self, obj, name):
            return name in {"recommendedMaxWorkingSetSize", "registryID", "supportsFamily:"}

        def supports_family(self, obj, family):
            return family in {1001, 1007, 2002, 3003, 5001}

        def release(self, obj):
            self.released.append(obj)

    api = FakeAPI()
    monkeypatch.setattr(_metal, "_ObjC", lambda: api)
    assert _metal.metal_devices() == [
        _metal.MetalDevice("Apple M1", 8.0, ["Apple 7", "Mac 2", "Common 3", "Metal 3"], 42)
    ]
    assert api.released == [3, 4]


def test_metal_objc_bridge_reads_device_properties(monkeypatch):
    class Function:
        def __init__(self, func):
            self.func = func

        def __call__(self, *args):
            return self.func(*args)

    selectors = {}
    name = ctypes.create_string_buffer(b"Apple M1")
    released = []

    def selector(raw):
        decoded = raw.decode("ascii")
        for value, existing in selectors.items():
            if existing == decoded:
                return value
        value = len(selectors) + 10
        selectors[value] = decoded
        return value

    def dispatch(obj, sel, arg):
        method = selectors[sel]
        if method == "alloc":
            return 2
        if method == "init":
            return 3
        if method == "count":
            return 1
        if method == "objectAtIndex:":
            return 5
        if method == "name":
            return 6
        if method == "UTF8String":
            return ctypes.addressof(name)
        if method == "respondsToSelector:":
            return 1
        if method == "recommendedMaxWorkingSetSize":
            return 8 * 1024**3
        if method == "registryID":
            return 0x123456789
        if method == "supportsFamily:":
            return int(arg in {1007, 2002, 3003, 5001})
        if method == "release":
            released.append(obj)
            return 0
        raise AssertionError(method)

    message_send = ctypes.CFUNCTYPE(
        ctypes.c_uint64, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint64
    )(dispatch)
    objc = SimpleNamespace(
        objc_getClass=Function(lambda raw: 1),
        sel_registerName=Function(selector),
        objc_msgSend=message_send,
    )
    metal = SimpleNamespace(MTLCopyAllDevices=Function(lambda: 4))
    monkeypatch.setattr(_metal.ctypes, "CDLL", lambda path: metal if path.endswith("/Metal") else objc)

    assert _metal.metal_devices() == [
        _metal.MetalDevice("Apple M1", 8.0, ["Apple 7", "Mac 2", "Common 3", "Metal 3"], 0x123456789)
    ]
    assert released == [4, 3]


def test_metal_probe_missing_selectors_remain_unknown(monkeypatch):
    class FakeAPI:
        objc = SimpleNamespace(objc_getClass=lambda name: 1)
        metal = SimpleNamespace(MTLCopyAllDevices=lambda: 3)

        def pointer(self, obj, name):
            return {(1, "alloc"): 2, (2, "init"): 4, (5, "name"): 6}[(obj, name)]

        def integer(self, obj, name):
            assert (obj, name) == (3, "count")
            return 1

        def indexed(self, obj, index):
            return 5

        def string(self, obj):
            return b"Apple M1"

        def responds(self, obj, name):
            return False

        def release(self, obj):
            pass

    monkeypatch.setattr(_metal, "_ObjC", FakeAPI)
    assert _metal.metal_devices() == [_metal.MetalDevice("Apple M1", None, None, None)]


def test_metal_probe_unavailable_runtime_is_logged(monkeypatch, caplog):
    def unavailable():
        raise OSError("missing Metal framework")

    monkeypatch.setattr(_metal, "_ObjC", unavailable)
    with caplog.at_level("DEBUG"):
        assert _metal.metal_devices() == []
    assert "missing Metal framework" in caplog.text


@pytest.mark.parametrize("value,expected", [("1536 MB", 1.5), ("8 GB", 8.0), ("bad", 0.0)])
def test_apple_memory_parser(value, expected):
    assert gpu_module._parse_memory(value) == expected
