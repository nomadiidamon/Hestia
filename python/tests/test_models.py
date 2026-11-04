import os
import subprocess
import sys

import pytest

import Hestia
from Hestia.models import (
    KNOWN_CATEGORIES,
    MODEL_DATABASE,
    ModelInfo,
    get_category,
    get_model_info,
    get_tier,
)
from Hestia.types import AcceleratorType, ModelSize


def test_enum_values():
    assert AcceleratorType("nvidia_cuda") is AcceleratorType.NVIDIA_CUDA
    assert [s.value for s in ModelSize] == ["tiny", "small", "medium", "large", "xlarge"]


def test_every_entry_has_required_keys():
    for tiers in MODEL_DATABASE.values():
        for entry in tiers.values():
            for key in (*KNOWN_CATEGORIES, "quantization", "batch_size", "context", "performance"):
                assert key in entry


@pytest.mark.parametrize("acc", list(MODEL_DATABASE))
@pytest.mark.parametrize("size", list(ModelSize))
def test_get_tier_always_resolves(acc, size):
    assert get_tier(acc, size)["models"]


def test_fallback_for_missing_tier():
    assert get_tier(AcceleratorType.INTEL_ONEAPI, ModelSize.XLARGE) is MODEL_DATABASE[
        AcceleratorType.INTEL_ONEAPI
    ][ModelSize.LARGE]


def test_unknown_accelerator_falls_back_to_cpu():
    entry = get_tier(AcceleratorType.QUALCOMM_HEXAGON, ModelSize.TINY)
    assert entry is MODEL_DATABASE[AcceleratorType.NONE][ModelSize.MEDIUM]


def test_get_category_unknown_is_empty():
    assert get_category(get_tier(AcceleratorType.NONE, ModelSize.TINY), "nope") == []


def test_get_model_info_single_and_all():
    info = get_model_info(AcceleratorType.NVIDIA_CUDA, ModelSize.SMALL)
    assert isinstance(info, ModelInfo)
    assert info.to_dict()["accelerator"] == "nvidia_cuda"
    assert info.get("tools")
    total = sum(len(t) for t in MODEL_DATABASE.values())
    assert len(get_model_info()) == total
    assert all(i.size is ModelSize.TINY for i in get_model_info(size=ModelSize.TINY))


def test_legacy_import_path():
    from Hestia.model_catalog import MODEL_DATABASE as legacy

    assert legacy is MODEL_DATABASE


def test_public_api():
    assert Hestia.get_model_info is get_model_info


def test_models_does_not_import_hardware():
    code = "import sys, Hestia.models; assert not any(m.startswith('Hestia.hardware') for m in sys.modules)"
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}
    subprocess.run([sys.executable, "-c", code], check=True, env=env)
