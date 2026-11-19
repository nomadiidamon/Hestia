"""Optional Metal device details on macOS."""

import ctypes
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)
_GIB = 1024**3
_MAX_DEVICES = 1024
_FAMILIES = (
    ("Apple", 1000, tuple(range(1001, 1011))),
    ("Mac", 2000, (2001, 2002)),
    ("Common", 3000, (3001, 3002, 3003)),
    ("Metal", 4998, (5001, 5002)),
)


@dataclass(frozen=True)
class MetalDevice:
    name: str
    recommended_working_set_gb: float | None
    families: list[str] | None
    registry_id: int | None


class _ObjC:
    def __init__(self):
        self.metal = ctypes.CDLL("/System/Library/Frameworks/Metal.framework/Metal")
        self.objc = ctypes.CDLL("/usr/lib/libobjc.A.dylib")
        self.objc.objc_getClass.argtypes = [ctypes.c_char_p]
        self.objc.objc_getClass.restype = ctypes.c_void_p
        self.objc.sel_registerName.argtypes = [ctypes.c_char_p]
        self.objc.sel_registerName.restype = ctypes.c_void_p
        self.metal.MTLCopyAllDevices.argtypes = []
        self.metal.MTLCopyAllDevices.restype = ctypes.c_void_p
        address = ctypes.cast(self.objc.objc_msgSend, ctypes.c_void_p).value
        if not address:
            raise OSError("Objective-C message dispatcher unavailable")
        pointer = ctypes.c_void_p
        self._pointer = ctypes.CFUNCTYPE(pointer, pointer, pointer)(address)
        self._integer = ctypes.CFUNCTYPE(ctypes.c_uint64, pointer, pointer)(address)
        self._indexed = ctypes.CFUNCTYPE(pointer, pointer, pointer, ctypes.c_ulong)(address)
        self._boolean = ctypes.CFUNCTYPE(ctypes.c_bool, pointer, pointer, pointer)(address)
        self._family = ctypes.CFUNCTYPE(ctypes.c_bool, pointer, pointer, ctypes.c_long)(address)
        self._string = ctypes.CFUNCTYPE(ctypes.c_char_p, pointer, pointer)(address)
        self._void = ctypes.CFUNCTYPE(None, pointer, pointer)(address)

    def selector(self, name: str):
        return self.objc.sel_registerName(name.encode("ascii"))

    def pointer(self, obj, name: str):
        return self._pointer(obj, self.selector(name))

    def integer(self, obj, name: str):
        return self._integer(obj, self.selector(name))

    def indexed(self, obj, index: int):
        return self._indexed(obj, self.selector("objectAtIndex:"), index)

    def responds(self, obj, name: str):
        return self._boolean(obj, self.selector("respondsToSelector:"), self.selector(name))

    def supports_family(self, obj, family: int):
        return self._family(obj, self.selector("supportsFamily:"), family)

    def string(self, obj):
        return self._string(obj, self.selector("UTF8String"))

    def release(self, obj):
        self._void(obj, self.selector("release"))


def metal_devices() -> list[MetalDevice]:
    """Return Metal device details; unavailable properties remain unknown."""
    try:
        api = _ObjC()
        pool_class = api.objc.objc_getClass(b"NSAutoreleasePool")
        if not pool_class:
            raise OSError("Objective-C autorelease pool unavailable")
        pool = api.pointer(api.pointer(pool_class, "alloc"), "init")
        if not pool:
            raise OSError("Could not create Objective-C autorelease pool")
        try:
            devices = api.metal.MTLCopyAllDevices()
            if not devices:
                logger.debug("Metal device enumeration returned no array")
                return []
            try:
                count = api.integer(devices, "count")
                if count > _MAX_DEVICES:
                    logger.debug("Metal returned an invalid device count: %s", count)
                    return []
                result = []
                for index in range(count):
                    device = api.indexed(devices, index)
                    if not device:
                        logger.debug("Metal device %s is unavailable", index)
                        continue
                    name_obj = api.pointer(device, "name")
                    raw_name = api.string(name_obj) if name_obj else None
                    if not raw_name:
                        logger.debug("Metal device %s has no name", index)
                        continue
                    name = raw_name.decode("utf-8")
                    working_set = None
                    if api.responds(device, "recommendedMaxWorkingSetSize"):
                        working_set = api.integer(device, "recommendedMaxWorkingSetSize") / _GIB
                    registry_id = None
                    if api.responds(device, "registryID"):
                        registry_id = api.integer(device, "registryID")
                    families = None
                    if api.responds(device, "supportsFamily:"):
                        families = []
                        for label, base, values in _FAMILIES:
                            for value in reversed(values):
                                if api.supports_family(device, value):
                                    families.append(f"{label} {value - base}")
                                    break
                    result.append(MetalDevice(name, working_set, families, registry_id))
                return result
            finally:
                api.release(devices)
        finally:
            api.release(pool)
    except (OSError, AttributeError, UnicodeError) as error:
        logger.debug("Metal device details unavailable: %s", error)
        return []
