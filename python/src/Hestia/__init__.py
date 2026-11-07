"""Hestia - system discovery and AI model intelligence."""

from importlib import import_module

from .models import ModelInfo, get_model_info
from .types import AcceleratorType, ModelSize


__version__ = "0.2.0"


__all__ = [
	"AcceleratorType",
	"GPUInfo",
	"HardwareDetector",
	"HardwareProfile",
	"ModelInfo",
	"ModelRecommendation",
	"ModelRecommender",
	"ModelSize",
	"__version__",
	"detect_hardware",
	"get_model_info",
	"get_system_summary",
	"print_hardware_report",
	"recommend_model",
]


_HARDWARE_EXPORTS = {"GPUInfo", "HardwareDetector", "HardwareProfile", "detect_hardware"}
_RECOMMENDER_EXPORTS = {
	"ModelRecommendation",
	"ModelRecommender",
	"get_system_summary",
	"print_hardware_report",
	"recommend_model",
}


def __getattr__(name: str):
	if name in _HARDWARE_EXPORTS:
		module = import_module(".hardware", __name__)
	elif name in _RECOMMENDER_EXPORTS:
		module = import_module(".recommender", __name__)
	else:
		raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
	value = getattr(module, name)
	globals()[name] = value
	return value
