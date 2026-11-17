"""Optional Intel Level Zero device UUID and PCI address discovery."""

import ctypes
import logging
import uuid

logger = logging.getLogger(__name__)

_UINT32 = ctypes.c_uint32
_HANDLE = ctypes.c_void_p
_MAX_DEVICES = 1024


class _DeviceProperties(ctypes.Structure):
    _fields_ = [
        ("stype", _UINT32),
        ("pNext", _HANDLE),
        ("type", _UINT32),
        ("vendorId", _UINT32),
        ("deviceId", _UINT32),
        ("flags", _UINT32),
        ("subdeviceId", _UINT32),
        ("coreClockRate", _UINT32),
        ("maxMemAllocSize", ctypes.c_uint64),
        ("maxHardwareContexts", _UINT32),
        ("maxCommandQueuePriority", _UINT32),
        ("numThreadsPerEU", _UINT32),
        ("physicalEUSimdWidth", _UINT32),
        ("numEUsPerSubslice", _UINT32),
        ("numSubslicesPerSlice", _UINT32),
        ("numSlices", _UINT32),
        ("timerResolution", ctypes.c_uint64),
        ("timestampValidBits", _UINT32),
        ("kernelTimestampValidBits", _UINT32),
        ("uuid", ctypes.c_ubyte * 16),
        ("name", ctypes.c_char * 256),
    ]


class _PciAddress(ctypes.Structure):
    _fields_ = [("domain", _UINT32), ("bus", _UINT32),
                ("device", _UINT32), ("function", _UINT32)]


class _PciSpeed(ctypes.Structure):
    _fields_ = [("genVersion", ctypes.c_int32), ("width", ctypes.c_int32),
                ("maxBandwidth", ctypes.c_int64)]


class _PciProperties(ctypes.Structure):
    _fields_ = [("stype", _UINT32), ("pNext", _HANDLE),
                ("address", _PciAddress), ("maxSpeed", _PciSpeed)]


class _LevelZeroError(Exception):
    pass


def _check(result: int, operation: str) -> None:
    if result:
        raise _LevelZeroError(f"{operation} failed with status 0x{result:08x}")


def _handles(function, *args) -> list:
    count = _UINT32()
    _check(function(*args, ctypes.byref(count), None), function.__name__)
    if count.value > _MAX_DEVICES:
        raise _LevelZeroError(f"{function.__name__} returned too many handles: {count.value}")
    if not count.value:
        return []
    handles = (_HANDLE * count.value)()
    _check(function(*args, ctypes.byref(count), handles), function.__name__)
    return list(handles)[:count.value]


def intel_device_uuids(system_name: str) -> list[tuple[str, str]]:
    """Return full PCI addresses and UUIDs for Intel GPUs exposed by Level Zero."""
    if system_name not in ("Windows", "Linux"):
        return []
    try:
        if system_name == "Windows":
            library = ctypes.WinDLL("ze_loader.dll")
        else:
            library = ctypes.CDLL("libze_loader.so.1")

        library.zeInit.argtypes = [_UINT32]
        library.zeInit.restype = _UINT32
        library.zeDriverGet.argtypes = [ctypes.POINTER(_UINT32), ctypes.POINTER(_HANDLE)]
        library.zeDriverGet.restype = _UINT32
        library.zeDeviceGet.argtypes = [_HANDLE, ctypes.POINTER(_UINT32), ctypes.POINTER(_HANDLE)]
        library.zeDeviceGet.restype = _UINT32
        library.zeDeviceGetProperties.argtypes = [_HANDLE, ctypes.POINTER(_DeviceProperties)]
        library.zeDeviceGetProperties.restype = _UINT32
        library.zeDevicePciGetPropertiesExt.argtypes = [_HANDLE, ctypes.POINTER(_PciProperties)]
        library.zeDevicePciGetPropertiesExt.restype = _UINT32

        _check(library.zeInit(1), "zeInit")
        devices = []
        for driver in _handles(library.zeDriverGet):
            try:
                driver_devices = _handles(library.zeDeviceGet, driver)
            except _LevelZeroError as error:
                logger.debug("Level Zero device enumeration failed: %s", error)
                continue
            for device in driver_devices:
                properties = _DeviceProperties(stype=3)
                status = library.zeDeviceGetProperties(device, ctypes.byref(properties))
                if status:
                    logger.debug("Level Zero device properties failed: 0x%08x", status)
                    continue
                if properties.type != 1 or properties.vendorId != 0x8086:
                    continue
                pci = _PciProperties(stype=0x10008)
                status = library.zeDevicePciGetPropertiesExt(device, ctypes.byref(pci))
                if status:
                    logger.debug("Level Zero PCI properties failed: 0x%08x", status)
                    continue
                address = pci.address
                if address.bus > 255 or address.device > 31 or address.function > 7:
                    logger.debug("Level Zero returned an invalid PCI address")
                    continue
                identifier = bytes(properties.uuid)
                if not any(identifier):
                    logger.debug("Level Zero returned an empty device UUID")
                    continue
                bus_id = f"{address.domain:04x}:{address.bus:02x}:{address.device:02x}.{address.function:x}"
                devices.append((bus_id, str(uuid.UUID(bytes=identifier))))
        return devices
    except (OSError, AttributeError, _LevelZeroError) as error:
        logger.debug("Level Zero GPU identification unavailable: %s", error)
        return []
