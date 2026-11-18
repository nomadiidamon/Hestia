"""Typed, extensible catalog of model tiers and individual model records."""

from dataclasses import dataclass
import math
import re
from types import MappingProxyType
from typing import Mapping, Optional

from ..types import AcceleratorType, ModelSize

DEFAULT_CATEGORIES = ("models", "thinking", "tools", "vision")


@dataclass(frozen=True)
class ModelRecord:
    """A model identifier and its family and total parameter count in billions."""

    name: str
    family: str
    parameters_billions: Optional[float]

    def __post_init__(self) -> None:
        if not self.name or not self.family:
            raise ValueError("Model name and family must not be empty")
        if self.parameters_billions is not None and (
            not math.isfinite(self.parameters_billions) or self.parameters_billions <= 0
        ):
            raise ValueError("Model parameter count must be finite and positive")

    @classmethod
    def from_name(cls, name: str) -> "ModelRecord":
        family, separator, tag = name.partition(":")
        match = re.match(r"^(\d+(?:\.\d+)?)b(?:-|$)", tag) if separator else None
        return cls(name, family, float(match.group(1)) if match else None)


@dataclass(frozen=True)
class ModelCatalogEntry:
    """One accelerator and memory tier, containing categorized model records."""

    accelerator: AcceleratorType
    size: ModelSize
    categories: Mapping[str, tuple[ModelRecord, ...]]
    quantization: str
    batch_size: int
    context: int
    performance: str

    def __post_init__(self) -> None:
        if not isinstance(self.accelerator, AcceleratorType) or not isinstance(self.size, ModelSize):
            raise TypeError("Catalog entries require an AcceleratorType and ModelSize")
        if not self.quantization or self.batch_size < 1 or self.context < 1 or not self.performance:
            raise ValueError("Catalog entries require quantization, positive batch size and context, and performance")
        if any(not isinstance(key, str) or not key or key != key.casefold() for key in self.categories):
            raise ValueError("Catalog category names must be nonempty lowercase strings")
        categories: dict[str, tuple[ModelRecord, ...]] = {key: () for key in DEFAULT_CATEGORIES}
        categories.update({key: tuple(models) for key, models in self.categories.items()})
        if any(not isinstance(model, ModelRecord) for models in categories.values() for model in models):
            raise TypeError("Catalog categories must contain ModelRecord instances")
        object.__setattr__(self, "categories", MappingProxyType(categories))

    def to_legacy(self) -> dict[str, object]:
        data: dict[str, object] = {
            category: [model.name for model in models] for category, models in self.categories.items()
        }
        data.update(quantization=self.quantization, batch_size=self.batch_size,
                    context=self.context, performance=self.performance)
        return data


class ModelCatalog:
    """Immutable collection of entries; pass a new catalog to customize recommendations."""

    def __init__(self, entries: list[ModelCatalogEntry]):
        index: dict[tuple[AcceleratorType, ModelSize], ModelCatalogEntry] = {}
        for entry in entries:
            key = (entry.accelerator, entry.size)
            if key in index:
                raise ValueError(f"Duplicate catalog entry: {key}")
            index[key] = entry
        self._entries = MappingProxyType(index)

    @property
    def entries(self) -> tuple[ModelCatalogEntry, ...]:
        return tuple(self._entries.values())

    def resolve(self, accelerator: AcceleratorType, size: ModelSize) -> ModelCatalogEntry:
        """Find the largest available tier no larger than the requested tier."""
        sizes = list(ModelSize)
        candidates = reversed(sizes[:sizes.index(size) + 1])
        for candidate in candidates:
            entry = self._entries.get((accelerator, candidate))
            if entry is not None:
                return entry
        if accelerator is not AcceleratorType.NONE:
            for candidate in reversed(sizes[:sizes.index(size) + 1]):
                entry = self._entries.get((AcceleratorType.NONE, candidate))
                if entry is not None:
                    return entry
        raise LookupError(f"No catalog tier at or below {size.value} for {accelerator.value} or CPU")

    def to_legacy(self) -> dict:
        database: dict = {}
        for entry in self.entries:
            database.setdefault(entry.accelerator, {})[entry.size] = entry.to_legacy()
        return database
