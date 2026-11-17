import os
import subprocess
import sys

import Hestia
from Hestia.hardware import GPUInfo, HardwareProfile
from Hestia.models.catalog import get_tier
from Hestia.recommender import ModelRecommendation, ModelRecommender
from Hestia.types import AcceleratorType, ModelSize


def test_recommender_selects_tier_and_catalog_data():
    profile = HardwareProfile(
        available_for_models_gb=6,
        primary_accelerator=AcceleratorType.NVIDIA_CUDA,
        cpu_cores_physical=4,
        cpu_cores_logical=8,
    )
    result = ModelRecommender(profile).recommend()
    expected = get_tier(AcceleratorType.NVIDIA_CUDA, ModelSize.MEDIUM)
    assert result.model_size is ModelSize.MEDIUM
    assert result.recommended_models == expected["models"]
    assert result.max_context_tokens == expected["context"]
    assert "Accelerator: nvidia_cuda" in result.reasoning


def test_recommender_uses_catalog_fallback_for_unknown_accelerator():
    profile = HardwareProfile(
        available_for_models_gb=1,
        primary_accelerator=AcceleratorType.QUALCOMM_HEXAGON,
    )
    result = Hestia.recommend_model(profile)
    assert result.model_size is ModelSize.TINY
    assert result.recommended_models == get_tier(
        AcceleratorType.QUALCOMM_HEXAGON, ModelSize.TINY
    )["models"]


def test_memory_tier_boundaries():
    assert ModelRecommender(HardwareProfile(available_for_models_gb=2)).recommend().model_size is ModelSize.SMALL
    assert ModelRecommender(HardwareProfile(available_for_models_gb=4)).recommend().model_size is ModelSize.MEDIUM
    assert ModelRecommender(HardwareProfile(available_for_models_gb=12)).recommend().model_size is ModelSize.LARGE
    assert ModelRecommender(HardwareProfile(available_for_models_gb=40)).recommend().model_size is ModelSize.XLARGE


def test_recommendation_serialization_and_report(capsys):
    profile = HardwareProfile(available_for_models_gb=1)
    recommendation = Hestia.recommend_model(profile)
    assert isinstance(recommendation, ModelRecommendation)
    assert recommendation.to_dict()["model_size"] == "tiny"

    Hestia.print_hardware_report(profile, recommendation)
    output = capsys.readouterr().out
    assert "[SYS] Hardware" in output
    assert "None detected - CPU only" in output
    assert "[REC] Model Recommendation" in output


def test_report_includes_gpu_identifiers_and_unknown_values(capsys):
    profile = HardwareProfile(gpus=[
        GPUInfo(0, "GPU", AcceleratorType.NVIDIA_CUDA, 8, 0,
                compute_capability="8.6", driver_version="555",
                pci_bus_id="0000:01:00.0", uuid="gpu-id",
                pci_vendor_id="0x10de", pci_device_id="0x1234",
                pnp_device_id="PCI-instance"),
        GPUInfo(1, "Integrated", AcceleratorType.INTEL_ONEAPI, 0, None),
    ])
    Hestia.print_hardware_report(profile)
    output = capsys.readouterr().out
    assert "0.0 GB free" in output
    assert "n/a free" in output
    identifiers = {
        "Compute": "8.6", "Driver": "555", "PCI bus": "0000:01:00.0",
        "UUID": "gpu-id", "PCI vendor": "0x10de", "PCI device": "0x1234",
        "PNP device": "PCI-instance",
    }
    for label, value in identifiers.items():
        assert any(label in line and value in line for line in output.splitlines())
        assert any(label in line and "n/a" in line for line in output.splitlines())


def test_public_api_and_no_hardware_probing_during_import():
    assert Hestia.detect_hardware
    assert Hestia.HardwareProfile
    assert Hestia.ModelRecommender
    code = "import sys, Hestia; assert 'pynvml' not in sys.modules"
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}
    subprocess.run([sys.executable, "-c", code], check=True, env=env)