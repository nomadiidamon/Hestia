"""Structured snapshots of configured software discovery."""

from dataclasses import dataclass
from enum import Enum


class VersionProbeStatus(str, Enum):
	NOT_FOUND = "not_found"
	NOT_CHECKED = "not_checked"
	NOT_SUPPORTED = "not_supported"
	DETECTED = "detected"
	UNKNOWN = "unknown"
	FAILED = "failed"
	TIMED_OUT = "timed_out"


@dataclass(frozen=True)
class SoftwareTool:
	name: str
	executable_path: str | None
	version: str | None
	version_status: VersionProbeStatus
	message: str

	@property
	def present(self) -> bool:
		return self.executable_path is not None

	def to_dict(self) -> dict[str, object]:
		return {
			"name": self.name,
			"present": self.present,
			"executable_path": self.executable_path,
			"version": self.version,
			"version_status": self.version_status.value,
			"message": self.message,
		}


@dataclass(frozen=True)
class SoftwareProfile:
	tools: tuple[SoftwareTool, ...]

	def to_dict(self) -> dict[str, object]:
		return {"tools": [tool.to_dict() for tool in self.tools]}
