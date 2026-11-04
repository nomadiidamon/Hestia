"""Typed view over the model catalog."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

from ..types import AcceleratorType, ModelSize
from .catalog import KNOWN_CATEGORIES, MODEL_DATABASE, TierEntry, get_category, get_tier


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
        return ModelInfo.from_entry(accelerator, size, get_tier(accelerator, size))

    return [
        ModelInfo.from_entry(acc, sz, entry)
        for acc, tiers in MODEL_DATABASE.items()
        if accelerator is None or acc == accelerator
        for sz, entry in tiers.items()
        if size is None or sz == size
    ]
