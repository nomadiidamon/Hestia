"""@example hardware_03_simulated_gpus.py
Show integrated fallback and multiple GPUs without requiring specific hardware.
"""

import json
from types import SimpleNamespace
from unittest.mock import patch

import Hestia
from Hestia.hardware import gpu
from Hestia.types import AcceleratorType


integrated_result = SimpleNamespace(returncode=0, stdout=json.dumps({
    "Name": "Simulated AMD Radeon Graphics",
    "AdapterRAM": 2 * 1024**3,
    "DriverVersion": None,
    "PNPDeviceID": r"PCI\VEN_1002&DEV_1234\example",
    "LocationInfo": "PCI bus 0, device 2, function 0",
}))

with (
    patch.object(gpu, "_detect_nvidia", return_value=[]),
    patch.object(gpu, "_detect_amd", return_value=[]),
    patch.object(gpu, "_detect_intel_windows", return_value=[]),
    patch.object(gpu.subprocess, "run", return_value=integrated_result),
):
    integrated = gpu.detect_gpus(system_name="Windows")

multiple = [
    Hestia.GPUInfo(0, "Simulated GPU", AcceleratorType.NVIDIA_CUDA, 8, 6,
                   pci_bus_id="0000:01:00.0", uuid="GPU-example-1"),
    Hestia.GPUInfo(1, "Simulated GPU", AcceleratorType.NVIDIA_CUDA, 8, 4,
                   pci_bus_id="0000:02:00.0", uuid="GPU-example-2"),
]
def profiles():
    with patch.object(gpu, "detect_gpus", return_value=integrated):
        integrated_profile = Hestia.detect_hardware()
    with patch.object(gpu, "detect_gpus", return_value=multiple):
        multiple_profile = Hestia.detect_hardware()
    return integrated_profile, multiple_profile


def main():
    integrated_profile, multiple_profile = profiles()
    print("Simulated integrated GPU fallback")
    Hestia.print_hardware_report(integrated_profile)
    print("\nSimulated multiple GPUs")
    Hestia.print_hardware_report(multiple_profile)


if __name__ == "__main__":
    main()
