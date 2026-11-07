"""
Model recommendations derived from hardware profiles and the catalog.

@todo Update the recommendation logic to use the ModelInfo class.
@todo Update the ModelRecommender to take a set of variables to influence the recommendation logic.
@todo Create a generic recommendation interface that can be extended for different types of recommendations.
@todo Create a generic recommender class that can be extended for different types of recommendations.
"""

from dataclasses import asdict, dataclass
from typing import Optional

from .hardware import HardwareProfile
from .models.catalog import get_category, get_tier
from .types import AcceleratorType, ModelSize


@dataclass(frozen=True)
class ModelRecommendation:
    """Recommended catalog configuration for one hardware profile."""

    model_size: ModelSize
    recommended_models: list[str]
    thinking_models: list[str]
    tool_models: list[str]
    vision_models: list[str]
    max_context_tokens: int
    quantization_level: str
    batch_size: int
    estimated_performance: str
    reasoning: str

    def to_dict(self) -> dict:
        data = asdict(self)
        data["model_size"] = self.model_size.value
        return data


class ModelRecommender:
    """Choose an advisory model tier based on available model memory."""

    def __init__(self, profile: HardwareProfile):
        self.profile = profile

    def recommend(self) -> ModelRecommendation:
        size = _model_size(self.profile.available_for_models_gb)
        accelerator = self.profile.primary_accelerator
        entry = get_tier(accelerator, size)
        return ModelRecommendation(
            model_size=size,
            recommended_models=get_category(entry, "models"),
            thinking_models=get_category(entry, "thinking"),
            tool_models=get_category(entry, "tools"),
            vision_models=get_category(entry, "vision"),
            max_context_tokens=int(entry.get("context", 4096)),
            quantization_level=str(entry.get("quantization", "q4_k_m")),
            batch_size=int(entry.get("batch_size", 1)),
            estimated_performance=str(entry.get("performance", "Unknown")),
            reasoning=_reasoning(self.profile),
        )


def _model_size(available_gb: float) -> ModelSize:
    if available_gb < 2:
        return ModelSize.TINY
    if available_gb < 4:
        return ModelSize.SMALL
    if available_gb < 12:
        return ModelSize.MEDIUM
    if available_gb < 40:
        return ModelSize.LARGE
    return ModelSize.XLARGE


def _reasoning(profile: HardwareProfile) -> str:
    reasons = [
        f"Available memory: {profile.available_for_models_gb:.1f}GB",
        f"Accelerator: {profile.primary_accelerator.value}",
        f"CPU cores: {profile.cpu_cores_physical} physical, {profile.cpu_cores_logical} logical",
    ]
    if profile.gpus:
        devices = ", ".join(f"{item.name} ({item.total_memory_gb:.1f}GB)" for item in profile.gpus)
        reasons.append(f"GPUs: {devices}")
    return " | ".join(reasons)


def recommend_model(profile: HardwareProfile) -> ModelRecommendation:
    """Return a catalog recommendation for a hardware profile."""
    return ModelRecommender(profile).recommend()


def get_system_summary() -> dict:
    """Return detected hardware and its corresponding recommendation."""
    from .hardware import detect_hardware

    profile = detect_hardware()
    recommendation = recommend_model(profile)
    return {"hardware": profile.to_dict(), "recommendation": recommendation.to_dict()}


def print_hardware_report(
    profile: HardwareProfile,
    recommendation: Optional[ModelRecommendation] = None,
) -> None:
    """Print a human-readable hardware summary and optional recommendation."""
    print("\n" + "=" * 50)
    print("[SYS] Hardware")
    print("=" * 50)
    print(f"CPU:       {profile.cpu_brand}")
    print(f"Cores:     {profile.cpu_cores_physical} physical / {profile.cpu_cores_logical} logical")
    print(f"Frequency: {profile.cpu_frequency_ghz:.2f} GHz")
    print(f"\nRAM:       {profile.ram_total_gb:.1f} GB total  |  {profile.ram_available_gb:.1f} GB available")
    if profile.gpus:
        print(f"\nGPUs ({len(profile.gpus)} detected):")
        for item in profile.gpus:
            print(f"  [{item.index}] {item.name}")
            print(f"       Type:   {item.accelerator.value}")
            print(f"       VRAM:   {item.total_memory_gb:.1f} GB total  |  {item.free_memory_gb:.1f} GB free")
            if item.compute_capability:
                print(f"       Compute: {item.compute_capability}")
            if item.driver_version:
                print(f"       Driver:  {item.driver_version}")
    else:
        print("\nGPU:       None detected - CPU only")
    print(f"\nPlatform:  {profile.platform_name} {profile.platform_version}")
    print(f"Python:    {profile.python_version}")
    print(f"Accelerator: {profile.primary_accelerator.value}")
    print(f"Available for models: {profile.available_for_models_gb:.1f} GB")
    if recommendation is not None:
        print("\n" + "=" * 50)
        print("[REC] Model Recommendation")
        print("=" * 50)
        print(f"Tier:         {recommendation.model_size.value}")
        print(f"Quantization: {recommendation.quantization_level}")
        print(f"Batch size:   {recommendation.batch_size}")
        print(f"Max context:  {recommendation.max_context_tokens:,} tokens")
        print(f"Performance:  {recommendation.estimated_performance}")
        print(f"\nGeneral:      {', '.join(recommendation.recommended_models)}")
        if recommendation.thinking_models:
            print(f"Thinking:     {', '.join(recommendation.thinking_models)}")
        if recommendation.tool_models:
            print(f"Tool use:     {', '.join(recommendation.tool_models)}")
        if recommendation.vision_models:
            print(f"Vision:       {', '.join(recommendation.vision_models)}")
        print(f"\nReasoning:    {recommendation.reasoning}")