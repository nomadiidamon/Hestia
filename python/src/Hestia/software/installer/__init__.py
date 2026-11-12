"""Caller-directed software installation framework."""

from .core import (
	InstallActionResult,
	InstallActionStatus,
	InstallAuthorization,
	InstallOutcome,
	InstallPlan,
	InstallProgress,
	InstallProgressTracker,
	InstallReport,
	InstallRequest,
	InstallationBackend,
	Installer,
)

__all__ = [
	"InstallActionResult",
	"InstallActionStatus",
	"InstallAuthorization",
	"InstallOutcome",
	"InstallPlan",
	"InstallProgress",
	"InstallProgressTracker",
	"InstallReport",
	"InstallRequest",
	"InstallationBackend",
	"Installer",
]