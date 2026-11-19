"""Software inventory, dependency checks, and environment tooling."""

from . import dependency, doctor, installer
from .catalog import SOFTWARE_CATALOG, SoftwareCommand, SoftwareDefinition
from .detection import detect_software
from .profile import SoftwareProfile, SoftwareTool, VersionProbeStatus

__all__ = [
	"SOFTWARE_CATALOG", "SoftwareCommand", "SoftwareDefinition", "SoftwareProfile", "SoftwareTool",
	"VersionProbeStatus", "detect_software", "dependency", "doctor", "installer",
]