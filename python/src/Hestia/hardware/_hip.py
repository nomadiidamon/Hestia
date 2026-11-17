"""Optional AMD HIP device UUID and PCI address discovery."""

import ctypes
import ctypes.util
import logging
import uuid

logger = logging.getLogger(__name__)
_MAX_DEVICES = 1024


class _HipUUID(ctypes.Structure):
    _fields_ = [("bytes", ctypes.c_ubyte * 16)]


def _load_runtime(system_name: str):
    if system_name == "Windows":
        names = ["amdhip64.dll"]
    elif system_name == "Linux":
        detected = ctypes.util.find_library("amdhip64")
        names = [name for name in (detected, "libamdhip64.so", "libamdhip64.so.7",
                                   "libamdhip64.so.6", "libamdhip64.so.5") if name]
    else:
        return None
    for name in dict.fromkeys(names):
        try:
            return ctypes.CDLL(name)
        except OSError as error:
            logger.debug("HIP runtime %s unavailable: %s", name, error)
    return None


def amd_device_uuids(system_name: str) -> list[tuple[str, str]]:
    """Return HIP-reported PCI addresses and UUIDs for available AMD devices."""
    try:
        library = _load_runtime(system_name)
        if library is None:
            return []
        library.hipGetDeviceCount.argtypes = [ctypes.POINTER(ctypes.c_int)]
        library.hipGetDeviceCount.restype = ctypes.c_int
        library.hipDeviceGet.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int]
        library.hipDeviceGet.restype = ctypes.c_int
        library.hipDeviceGetPCIBusId.argtypes = [ctypes.POINTER(ctypes.c_char), ctypes.c_int, ctypes.c_int]
        library.hipDeviceGetPCIBusId.restype = ctypes.c_int
        library.hipDeviceGetUuid.argtypes = [ctypes.POINTER(_HipUUID), ctypes.c_int]
        library.hipDeviceGetUuid.restype = ctypes.c_int

        count = ctypes.c_int()
        status = library.hipGetDeviceCount(ctypes.byref(count))
        if status:
            logger.debug("HIP device enumeration failed: %s", status)
            return []
        if count.value < 0 or count.value > _MAX_DEVICES:
            logger.debug("HIP returned an invalid device count: %s", count.value)
            return []

        devices = []
        for ordinal in range(count.value):
            device = ctypes.c_int()
            status = library.hipDeviceGet(ctypes.byref(device), ordinal)
            if status:
                logger.debug("HIP device %s lookup failed: %s", ordinal, status)
                continue
            bus_id = ctypes.create_string_buffer(32)
            status = library.hipDeviceGetPCIBusId(bus_id, len(bus_id), ordinal)
            if status:
                logger.debug("HIP device %s PCI lookup failed: %s", ordinal, status)
                continue
            identifier = _HipUUID()
            status = library.hipDeviceGetUuid(ctypes.byref(identifier), device.value)
            if status:
                logger.debug("HIP device %s UUID lookup failed: %s", ordinal, status)
                continue
            raw_uuid = bytes(identifier.bytes)
            if not any(raw_uuid):
                logger.debug("HIP device %s returned an empty UUID", ordinal)
                continue
            try:
                address = bus_id.value.decode("ascii")
            except UnicodeDecodeError as error:
                logger.debug("HIP device %s returned a malformed PCI address: %s", ordinal, error)
                continue
            devices.append((address, str(uuid.UUID(bytes=raw_uuid))))
        return devices
    except (OSError, AttributeError) as error:
        logger.debug("HIP GPU identification unavailable: %s", error)
        return []
