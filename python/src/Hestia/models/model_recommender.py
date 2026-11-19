"""Model recommendations derived from hardware profiles and the catalog."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import re
from typing import TYPE_CHECKING, AbstractSet, Optional

from ..recommender import Recommendation, RecommendationWeight, Recommender
from ..types import AcceleratorType, ModelSize
from .catalog import MODEL_CATALOG
from .info import ModelInfo
from .model_catalog import ModelCatalog, ModelRecord

if TYPE_CHECKING:
    from ..hardware import HardwareProfile


@dataclass(frozen=True)
class ModelRecommendationWeight(RecommendationWeight):
    """Model constraints; parameter counts are total billions, including MoE models."""

    max_memory_gb: Optional[float] = None
    max_model_size: Optional[ModelSize] = None
    max_parameters_billions: Optional[float] = None
    include_capabilities: AbstractSet[str] = frozenset()
    exclude_capabilities: AbstractSet[str] = frozenset()
    include_families: AbstractSet[str] = frozenset()
    exclude_families: AbstractSet[str] = frozenset()
    preferred_families: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("max_memory_gb", "max_parameters_billions"):
            value = getattr(self, name)
            if value is not None and (not math.isfinite(value) or value <= 0):
                raise ValueError(f"{name} must be finite and positive")
        if self.max_model_size is not None and not isinstance(self.max_model_size, ModelSize):
            raise TypeError("max_model_size must be a ModelSize")
        for name in ("include_capabilities", "exclude_capabilities", "include_families", "exclude_families"):
            value = getattr(self, name)
            if isinstance(value, str) or not all(isinstance(item, str) and item for item in value):
                raise ValueError(f"{name} must contain nonempty strings")
            object.__setattr__(self, name, frozenset(item.casefold() for item in value))
        if isinstance(self.preferred_families, str) or not all(
            isinstance(item, str) and item for item in self.preferred_families
        ):
            raise ValueError("preferred_families must contain nonempty strings")
        object.__setattr__(self, "preferred_families", tuple(item.casefold() for item in self.preferred_families))
        if self.include_capabilities & self.exclude_capabilities:
            raise ValueError("A capability cannot be both included and excluded")
        if self.include_families & self.exclude_families:
            raise ValueError("A family cannot be both included and excluded")


@dataclass(frozen=True)
class ModelRecommendation(Recommendation):
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
    categories: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["model_size"] = self.model_size.value
        return data


class ModelRecommender(Recommender[ModelRecommendation]):
    """Choose an advisory model tier based on available model memory.

    @bug Runtime type-hint resolution fails because HardwareProfile is imported
    only during type checking.
    @todo Make HardwareProfile annotations resolvable at runtime without
    eagerly importing hardware when the models package is imported.
    """

    def __init__(
        self,
        profile: HardwareProfile,
        weight: Optional[ModelRecommendationWeight] = None,
        catalog: Optional[ModelCatalog] = None,
    ):
        self.profile = profile
        self.weight = weight if weight is not None else ModelRecommendationWeight()
        self.catalog = catalog if catalog is not None else MODEL_CATALOG

    def recommend(self) -> ModelRecommendation:
        """Return a recommendation for the selected catalog tier.

        @bug Filtering only the selected tier can yield an empty result even
        when a smaller tier contains suitable models.
        @todo Check eligible smaller tiers before reporting that all catalog
        entries were disregarded.
        """
        available = self.profile.available_for_models_gb
        if not math.isfinite(available) or available < 0:
            raise ValueError("available_for_models_gb must be finite and nonnegative")
        budget = min(available, self.weight.max_memory_gb) if self.weight.max_memory_gb is not None else available
        size = _model_size(budget)
        if self.weight.max_model_size is not None:
            sizes = list(ModelSize)
            size = sizes[min(sizes.index(size), sizes.index(self.weight.max_model_size))]
        accelerator = self.profile.primary_accelerator
        entry = self.catalog.resolve(accelerator, size)
        info = ModelInfo.from_catalog_entry(entry)
        known_capabilities = {category for item in self.catalog.entries for category in item.categories}
        unknown = (self.weight.include_capabilities | self.weight.exclude_capabilities) - known_capabilities
        if unknown:
            raise ValueError(f"Unknown model capabilities: {', '.join(sorted(unknown))}")

        included = {model.name for category in self.weight.include_capabilities
                    for model in entry.categories.get(category, ())}
        excluded = {model.name for category in self.weight.exclude_capabilities
                    for model in entry.categories.get(category, ())}

        def acceptable(model: ModelRecord) -> bool:
            family = model.family.casefold()
            return (
                model.name not in excluded
                and (not self.weight.include_capabilities or model.name in included)
                and (not self.weight.include_families or family in self.weight.include_families)
                and family not in self.weight.exclude_families
                and model.parameters_billions is not None
                and (self.weight.max_parameters_billions is None
                     or model.parameters_billions <= self.weight.max_parameters_billions)
                and _estimated_memory_gb(model.parameters_billions, info.quantization) <= budget
            )

        preference = {family: index for index, family in enumerate(self.weight.preferred_families)}

        def category(name: str) -> list[str]:
            models = [model for model in entry.categories.get(name, ()) if acceptable(model)]
            models.sort(key=lambda model: preference.get(model.family.casefold(), len(preference)))
            return [model.name for model in models]

        categories = {name: category(name) for name in entry.categories}
        reasoning = _reasoning(self.profile)
        reasoning += f" | Memory budget: {budget:.1f}GB (estimated weights; runtime memory may be higher)"
        if entry.size is not size or entry.accelerator is not accelerator:
            reasoning += f" | Catalog fallback: {entry.accelerator.value}/{entry.size.value}"
        if not any(categories.values()):
            reasoning += " | All catalog entries were disregarded due to constraints or unknown model size."
        return ModelRecommendation(
            model_size=info.size,
            recommended_models=categories.get("models", []),
            thinking_models=categories.get("thinking", []),
            tool_models=categories.get("tools", []),
            vision_models=categories.get("vision", []),
            max_context_tokens=info.context,
            quantization_level=info.quantization,
            batch_size=info.batch_size,
            estimated_performance=info.performance,
            reasoning=reasoning,
            categories=categories,
        )


def _estimated_memory_gb(parameters_billions: float, quantization: str) -> float:
    """Estimate weight storage in GiB with 25% overhead; runtime memory can be higher.

    @bug Catalog entries accept quantizations such as fp16 that this estimator
    cannot handle, causing recommendation to fail.
    @todo Support additional quantizations or validate them when constructing
    catalog entries.
    @note The estimate does not guarantee that runtime memory fits the budget.
    """
    match = re.match(r"^q([1-8])(?:_|$)", quantization.lower())
    if match is None:
        raise ValueError(f"Cannot estimate memory for quantization {quantization!r}")
    return parameters_billions * 1_000_000_000 * int(match.group(1)) / 8 * 1.25 / 1024**3


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


def recommend_model(
    profile: HardwareProfile,
    weight: Optional[ModelRecommendationWeight] = None,
) -> ModelRecommendation:
    """Return a catalog recommendation for a hardware profile."""
    return ModelRecommender(profile, weight).recommend()


def get_system_summary() -> dict:
    """Return detected hardware and its corresponding recommendation."""
    from ..hardware import detect_hardware

    profile = detect_hardware()
    recommendation = recommend_model(profile)
    return {"hardware": profile.to_dict(), "recommendation": recommendation.to_dict()}


def print_hardware_report(
    profile: HardwareProfile,
    recommendation: Optional[ModelRecommendation] = None,
) -> None:
    """Print a human-readable hardware summary and optional recommendation.

    @bug Custom recommendation categories are omitted from the report.
    @todo Include custom categories when printing recommendations.
    """
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
            free_vram = f"{item.free_memory_gb:.1f} GB" if item.free_memory_gb is not None else "n/a"
            print(f"       VRAM:   {item.total_memory_gb:.1f} GB total  |  {free_vram} free")
            print(f"       Compute:    {item.compute_capability if item.compute_capability is not None else 'n/a'}")
            print(f"       Driver:     {item.driver_version if item.driver_version is not None else 'n/a'}")
            print(f"       PCI bus:    {item.pci_bus_id if item.pci_bus_id is not None else 'n/a'}")
            print(f"       UUID:       {item.uuid if item.uuid is not None else 'n/a'}")
            print(f"       PCI vendor: {item.pci_vendor_id if item.pci_vendor_id is not None else 'n/a'}")
            print(f"       PCI device: {item.pci_device_id if item.pci_device_id is not None else 'n/a'}")
            print(f"       PNP device: {item.pnp_device_id if item.pnp_device_id is not None else 'n/a'}")
            if item.accelerator is AcceleratorType.APPLE_METAL:
                working_set = item.metal_recommended_working_set_gb
                working_set_text = f"{working_set:.1f} GB" if working_set is not None else "n/a"
                families = ", ".join(item.metal_gpu_families) if item.metal_gpu_families else "n/a"
                registry = item.metal_registry_id if item.metal_registry_id is not None else "n/a"
                print(f"       Metal recommended working set: {working_set_text}")
                print(f"       Metal GPU families:            {families}")
                print(f"       Metal registry ID:             {registry}")
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