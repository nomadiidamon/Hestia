"""@example recommendation_04_constraints_json.py
Serialize a constrained model recommendation.
"""

import json
from Hestia.hardware import HardwareProfile
from Hestia.models import ModelRecommendationWeight, recommend_model
from Hestia.types import AcceleratorType, ModelSize

profile = HardwareProfile(available_for_models_gb=12, primary_accelerator=AcceleratorType.NVIDIA_CUDA)
weight = ModelRecommendationWeight(
    max_memory_gb=6, max_model_size=ModelSize.MEDIUM, max_parameters_billions=8,
    include_capabilities={"tools"}, exclude_capabilities={"vision"}, include_families={"qwen3"},
)
print(json.dumps(recommend_model(profile, weight).to_dict(), indent=2))