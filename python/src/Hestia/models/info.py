"""Typed view over the model catalog."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

from ..types import AcceleratorType, ModelSize
from .catalog import KNOWN_CATEGORIES, MODEL_CATALOG, TierEntry, get_category
from .model_catalog import ModelCatalogEntry


@dataclass(frozen=True)
class ModelInfo:
    """Catalog entry for one accelerator + memory tier."""

    accelerator: AcceleratorType
    size: ModelSize
    categories: Dict[str, List[str]] = field(default_factory=dict)
    quantization: str = ""
    batch_size: int = 1
    context: int = 0
    performance: str = ""

    @classmethod
    def from_entry(
        cls, accelerator: AcceleratorType, size: ModelSize, entry: TierEntry
    ) -> "ModelInfo":
        return cls(
            accelerator=accelerator,
            size=size,
            categories={c: list(get_category(entry, c)) for c in KNOWN_CATEGORIES},
            quantization=str(entry.get("quantization", "")),
            batch_size=int(entry.get("batch_size", 1)),
            context=int(entry.get("context", 0)),
            performance=str(entry.get("performance", "")),
        )

    @classmethod
    def from_catalog_entry(cls, entry: ModelCatalogEntry) -> "ModelInfo":
        return cls(
            accelerator=entry.accelerator,
            size=entry.size,
            categories={c: [model.name for model in models] for c, models in entry.categories.items()},
            quantization=entry.quantization,
            batch_size=entry.batch_size,
            context=entry.context,
            performance=entry.performance,
        )

    def get(self, category: str) -> List[str]:
        return list(self.categories.get(category, []))

    def to_dict(self) -> dict:
        return {
            "accelerator": self.accelerator.value,
            "size": self.size.value,
            "categories": {k: list(v) for k, v in self.categories.items()},
            "quantization": self.quantization,
            "batch_size": self.batch_size,
            "context": self.context,
            "performance": self.performance,
        }


def get_model_info(
    accelerator: Optional[AcceleratorType] = None,
    size: Optional[ModelSize] = None,
) -> Union[ModelInfo, List[ModelInfo]]:
    """Return one ModelInfo when both arguments are given, else all matching entries.

    A single lookup uses get_tier() and so applies its fallback rules.
    """
    if accelerator is not None and size is not None:
        return ModelInfo.from_catalog_entry(MODEL_CATALOG.resolve(accelerator, size))

    return [
        ModelInfo.from_catalog_entry(entry)
        for entry in MODEL_CATALOG.entries
        if accelerator is None or entry.accelerator == accelerator
        if size is None or entry.size == size
    ]
