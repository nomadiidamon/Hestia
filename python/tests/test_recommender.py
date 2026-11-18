import os
import subprocess
import sys

import Hestia
import pytest
from Hestia.hardware import GPUInfo, HardwareProfile
from Hestia.models import ModelCatalog, ModelCatalogEntry, ModelRecord
from Hestia.recommender import ModelRecommendation, ModelRecommendationWeight, ModelRecommender
from Hestia.types import AcceleratorType, ModelSize


def test_recommender_selects_tier_and_catalog_data():
    profile = HardwareProfile(
        available_for_models_gb=6,
        primary_accelerator=AcceleratorType.NVIDIA_CUDA,
        cpu_cores_physical=4,
        cpu_cores_logical=8,
    )
    result = ModelRecommender(profile).recommend()
    assert result.model_size is ModelSize.MEDIUM
    assert "qwen3:8b" in result.recommended_models
    assert "mistral-nemo:12b" not in result.recommended_models
    assert result.max_context_tokens == 32768
    assert "Accelerator: nvidia_cuda" in result.reasoning


def test_recommender_uses_catalog_fallback_for_unknown_accelerator():
    profile = HardwareProfile(
        available_for_models_gb=1,
        primary_accelerator=AcceleratorType.QUALCOMM_HEXAGON,
    )
    result = Hestia.recommend_model(profile)
    assert result.model_size is ModelSize.TINY
    assert result.recommended_models == ["qwen3:0.6b"]
    assert "Catalog fallback: none/tiny" in result.reasoning


def test_memory_tier_boundaries():
    for memory, size in [(2, ModelSize.SMALL), (4, ModelSize.MEDIUM),
                         (12, ModelSize.LARGE), (40, ModelSize.XLARGE)]:
        profile = HardwareProfile(available_for_models_gb=memory, primary_accelerator=AcceleratorType.NVIDIA_CUDA)
        assert ModelRecommender(profile).recommend().model_size is size


def test_weights_filter_capabilities_families_size_and_memory():
    profile = HardwareProfile(available_for_models_gb=24, primary_accelerator=AcceleratorType.NVIDIA_CUDA)
    weight = ModelRecommendationWeight(
        max_memory_gb=6, max_model_size=ModelSize.MEDIUM, max_parameters_billions=8,
        include_capabilities={"tools"}, exclude_capabilities={"vision"},
        include_families={"QWEN3"}, exclude_families={"llama3.1"},
    )
    result = Hestia.recommend_model(profile, weight)
    assert result.model_size is ModelSize.MEDIUM
    assert result.recommended_models == ["qwen3:8b"]
    assert result.tool_models == ["qwen3:8b"]
    assert result.vision_models == []
    assert "Memory budget: 6.0GB" in result.reasoning


def test_empty_recommendation_and_unknown_parameters():
    entry = ModelCatalogEntry(
        AcceleratorType.NONE, ModelSize.TINY,
        {"models": (ModelRecord("unknown:latest", "unknown", None),)},
        "q4_k_m", 1, 4096, "Slow",
    )
    result = ModelRecommender(HardwareProfile(available_for_models_gb=1), catalog=ModelCatalog([entry])).recommend()
    assert result.recommended_models == []
    assert "All catalog entries were disregarded" in result.reasoning


def test_preferred_family_orders_models_and_constraints_are_validated():
    profile = HardwareProfile(available_for_models_gb=8, primary_accelerator=AcceleratorType.NVIDIA_CUDA)
    result = Hestia.recommend_model(profile, ModelRecommendationWeight(preferred_families=("mistral",)))
    assert result.recommended_models[0] == "mistral:7b"
    with pytest.raises(ValueError):
        ModelRecommendationWeight(max_memory_gb=float("nan"))
    with pytest.raises(ValueError):
        ModelRecommendationWeight(include_families={"qwen3"}, exclude_families={"QWEN3"})
    with pytest.raises(ValueError, match="Unknown model capabilities"):
        Hestia.recommend_model(profile, ModelRecommendationWeight(include_capabilities={"not-a-capability"}))


def test_custom_catalog_supports_extra_categories():
    model = ModelRecord("example:1b", "example", 1)
    entry = ModelCatalogEntry(AcceleratorType.NONE, ModelSize.TINY, {"coding": (model,)},
                              "q4_k_m", 1, 4096, "Slow")
    result = ModelRecommender(
        HardwareProfile(available_for_models_gb=1),
        ModelRecommendationWeight(include_capabilities={"coding"}),
        ModelCatalog([entry]),
    ).recommend()
    assert result.categories["coding"] == ["example:1b"]
    assert "disregarded" not in result.reasoning


def test_budget_and_parameter_boundaries():
    profile = HardwareProfile(available_for_models_gb=8, primary_accelerator=AcceleratorType.NVIDIA_CUDA)
    limit = 8 * 1_000_000_000 * 4 / 8 * 1.25 / 1024**3
    at_limit = Hestia.recommend_model(profile, ModelRecommendationWeight(max_memory_gb=limit))
    below_limit = Hestia.recommend_model(profile, ModelRecommendationWeight(max_memory_gb=limit - 0.01))
    assert "qwen3:8b" in at_limit.recommended_models
    assert "qwen3:8b" not in below_limit.recommended_models
    capped = Hestia.recommend_model(profile, ModelRecommendationWeight(max_parameters_billions=7))
    assert "mistral:7b" in capped.recommended_models
    assert "qwen3:8b" not in capped.recommended_models
    smaller = Hestia.recommend_model(profile, ModelRecommendationWeight(max_model_size=ModelSize.TINY))
    assert smaller.model_size is ModelSize.TINY


def test_generic_base_classes_and_legacy_imports():
    from Hestia.models import ModelRecommendation as NewRecommendation
    from Hestia.models import ModelRecommender as NewRecommender
    assert NewRecommendation is ModelRecommendation
    assert NewRecommender is ModelRecommender
    assert issubclass(ModelRecommendation, Hestia.Recommendation)
    assert issubclass(ModelRecommender, Hestia.Recommender)
    assert issubclass(ModelRecommendationWeight, Hestia.RecommendationWeight)


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