import sys

import pytest

from Hestia.hardware import _metal


@pytest.mark.skipif(sys.platform != "darwin", reason="requires the macOS Metal framework")
def test_native_metal_probe_on_macos():
    devices = _metal.metal_devices()
    if not devices:
        pytest.skip("no Metal devices available")
    for device in devices:
        assert device.name
        if device.name == "Apple M1":
            assert device.recommended_working_set_gb is not None
            assert device.recommended_working_set_gb > 0
            assert device.families is not None
            assert "Apple 7" in device.families
            assert device.registry_id is not None
