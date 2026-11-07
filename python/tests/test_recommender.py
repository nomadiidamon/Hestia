import os
import subprocess
import sys

import Hestia
from Hestia.hardware import HardwareProfile
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
    assert "[REC] Model Recommendation" in output


def test_public_api_and_no_hardware_probing_during_import():
    assert Hestia.detect_hardware
    assert Hestia.HardwareProfile
    assert Hestia.ModelRecommender
    code = "import sys, Hestia; assert 'pynvml' not in sys.modules"
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}
    subprocess.run([sys.executable, "-c", code], check=True, env=env)