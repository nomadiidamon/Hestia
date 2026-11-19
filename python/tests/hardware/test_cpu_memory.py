from types import SimpleNamespace

from Hestia.hardware import cpu as cpu_module
from Hestia.hardware import memory as memory_module


def test_cpu_probe_reports_counts_frequency_and_brand(monkeypatch):
    monkeypatch.setattr(cpu_module.psutil, "cpu_count", lambda logical: 8 if logical else 4)
    monkeypatch.setattr(cpu_module.psutil, "cpu_freq", lambda: type("Frequency", (), {"current": 3200})())
    monkeypatch.setattr(cpu_module.platform, "processor", lambda: "Test CPU")
    result = cpu_module.detect_cpu()
    assert result == {
        "count": 8,
        "physical_cores": 4,
        "logical_cores": 8,
        "frequency_ghz": 3.2,
        "brand": "Test CPU",
    }


def test_cpu_probe_uses_macos_brand_when_processor_is_architecture(monkeypatch):
    monkeypatch.setattr(cpu_module.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(cpu_module.platform, "processor", lambda: "arm")
    monkeypatch.setattr(cpu_module.psutil, "cpu_count", lambda logical: 8)
    monkeypatch.setattr(cpu_module.psutil, "cpu_freq", lambda: None)
    monkeypatch.setattr(cpu_module.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=0, stdout="Apple M1\n",
    ))

    assert cpu_module.detect_cpu()["brand"] == "Apple M1"


def test_memory_probe_converts_bytes_and_degrades(monkeypatch):
    monkeypatch.setattr(memory_module.psutil, "virtual_memory", lambda: type(
        "Memory", (), {"total": 8 * 1024**3, "available": 3 * 1024**3}
    )())
    assert memory_module.detect_memory() == {"total_gb": 8.0, "available_gb": 3.0}
    monkeypatch.setattr(memory_module.psutil, "virtual_memory", lambda: (_ for _ in ()).throw(OSError()))
    assert memory_module.detect_memory() == {"total_gb": 0.0, "available_gb": 0.0}
