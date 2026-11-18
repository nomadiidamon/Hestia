"""Generic recommendation contracts and legacy model recommendation exports."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from importlib import import_module
from typing import Generic, TypeVar


class Recommendation(ABC):
    """A recommendation that can be serialized for consumers."""

    @abstractmethod
    def to_dict(self) -> dict:
        """Return a serialized recommendation."""


@dataclass(frozen=True)
class RecommendationWeight:
    """Base for domain-specific recommendation constraints and preferences."""


RecommendationT = TypeVar("RecommendationT", bound=Recommendation)


class Recommender(ABC, Generic[RecommendationT]):
    """Produce recommendations for a domain."""

    @abstractmethod
    def recommend(self) -> RecommendationT:
        """Return a recommendation."""


_MODEL_EXPORTS = {
    "ModelRecommendation",
    "ModelRecommendationWeight",
    "ModelRecommender",
    "get_system_summary",
    "print_hardware_report",
    "recommend_model",
}

__all__ = ["Recommendation", "RecommendationWeight", "Recommender", *_MODEL_EXPORTS]


def __getattr__(name: str):
    if name not in _MODEL_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(".models.model_recommender", __package__), name)
    globals()[name] = value
    return value
