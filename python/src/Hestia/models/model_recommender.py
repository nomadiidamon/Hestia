"""Model recommendations derived from hardware profiles and the catalog."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import re
from typing import TYPE_CHECKING, AbstractSet, Optional

from Auctor.Stylus.Colors import Colors

from .._terminal import styled
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
    """
    def label(text: str) -> str:
        return styled(text, Colors.OKCYAN)

    print("\n" + "=" * 50)
    print(styled("[SYS] Hardware", Colors.BOLD, Colors.OKCYAN))
    print("=" * 50)
    print(f"{label('CPU:')}       {profile.cpu_brand}")
    print(f"{label('Cores:')}     {profile.cpu_cores_physical} physical / {profile.cpu_cores_logical} logical")
    print(f"{label('Frequency:')} {profile.cpu_frequency_ghz:.2f} GHz")
    print(f"\n{label('RAM:')}       {profile.ram_total_gb:.1f} GB total  |  {profile.ram_available_gb:.1f} GB available")
    if profile.gpus:
        print("\n" + label('GPUs') + f" ({len(profile.gpus)} detected):")
        for item in profile.gpus:
            print(f"  {label(f'[{item.index}]')} {item.name}")
            print(f"       {label('Type:')}   {item.accelerator.value}")
            free_vram = f"{item.free_memory_gb:.1f} GB" if item.free_memory_gb is not None else "n/a"
            print(f"       {label('VRAM:')}   {item.total_memory_gb:.1f} GB total  |  {free_vram} free")
            print(f"       {label('Compute:')}    {item.compute_capability if item.compute_capability is not None else 'n/a'}")
            print(f"       {label('Driver:')}     {item.driver_version if item.driver_version is not None else 'n/a'}")
            print(f"       {label('PCI bus:')}    {item.pci_bus_id if item.pci_bus_id is not None else 'n/a'}")
            print(f"       {label('UUID:')}       {item.uuid if item.uuid is not None else 'n/a'}")
            print(f"       {label('PCI vendor:')} {item.pci_vendor_id if item.pci_vendor_id is not None else 'n/a'}")
            print(f"       {label('PCI device:')} {item.pci_device_id if item.pci_device_id is not None else 'n/a'}")
            print(f"       {label('PNP device:')} {item.pnp_device_id if item.pnp_device_id is not None else 'n/a'}")
            if item.accelerator is AcceleratorType.APPLE_METAL:
                working_set = item.metal_recommended_working_set_gb
                working_set_text = f"{working_set:.1f} GB" if working_set is not None else "n/a"
                families = ", ".join(item.metal_gpu_families) if item.metal_gpu_families else "n/a"
                registry = item.metal_registry_id if item.metal_registry_id is not None else "n/a"
                print(f"       {label('Metal recommended working set:')} {working_set_text}")
                print(f"       {label('Metal GPU families:')}            {families}")
                print(f"       {label('Metal registry ID:')}             {registry}")
    else:
        print(f"\n{label('GPU:')}       None detected - CPU only")
    print(f"\n{label('Platform:')}  {profile.platform_name} {profile.platform_version}")
    print(f"{label('Python:')}    {profile.python_version}")
    print(f"{label('Accelerator:')} {profile.primary_accelerator.value}")
    print(f"{label('Available for models:')} {profile.available_for_models_gb:.1f} GB")
    if recommendation is not None:
        print("\n" + "=" * 50)
        print(styled("[REC] Model Recommendation", Colors.BOLD, Colors.OKGREEN))
        print("=" * 50)
        print(f"{label('Tier:')}         {recommendation.model_size.value}")
        print(f"{label('Quantization:')} {recommendation.quantization_level}")
        print(f"{label('Batch size:')}   {recommendation.batch_size}")
        print(f"{label('Max context:')}  {recommendation.max_context_tokens:,} tokens")
        print(f"{label('Performance:')}  {recommendation.estimated_performance}")
        categories = [
            ("General", recommendation.recommended_models),
            ("Thinking", recommendation.thinking_models),
            ("Tool use", recommendation.tool_models),
            ("Vision", recommendation.vision_models),
        ]
        known_categories = {"models", "thinking", "tools", "vision"}
        categories.extend(
            (name.replace("_", " ").title(), models)
            for name, models in recommendation.categories.items()
            if name not in known_categories
        )
        populated_categories = [(name, models) for name, models in categories if models]
        if populated_categories:
            for name, models in populated_categories:
                print("\n" + styled(f"{name}:", Colors.BOLD, Colors.OKGREEN))
                for model in models:
                    print(f"  - {model}")
        else:
            print(f"\n{label('Models:')} none")

        print("\n" + styled("Reasoning:", Colors.BOLD))
        if recommendation.reasoning:
            for reason in recommendation.reasoning.split(" | "):
                print(f"  - {reason}")
        else:
            print("  (not provided)")