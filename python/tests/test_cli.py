import json
from types import SimpleNamespace

import pytest

from Hestia import cli
from Hestia.types import AcceleratorType, ModelSize


def _profile(data):
    return SimpleNamespace(to_dict=lambda: data)


def test_hardware_json_outputs_profile_without_text_report(monkeypatch, capsys):
    profile = _profile({"cpu_brand": "Example CPU"})
    report_calls = []
    monkeypatch.setattr(cli.Hestia, "detect_hardware", lambda: profile)
    monkeypatch.setattr(
        cli.Hestia, "print_hardware_report",
        lambda *args: report_calls.append(args),
    )

    assert cli.main(["hardware", "--json"]) == 0
    assert report_calls == []
    assert json.loads(capsys.readouterr().out) == {"cpu_brand": "Example CPU"}


@pytest.mark.parametrize(("option", "probe_versions"), [(None, True), ("--no-version-probes", False)])
def test_software_json_controls_version_probes(monkeypatch, capsys, option, probe_versions):
    profile = _profile({"tools": []})
    calls = []

    def detect_software(*, probe_versions):
        calls.append(probe_versions)
        return profile

    monkeypatch.setattr(cli.Hestia, "detect_software", detect_software)
    argv = ["software"]
    if option:
        argv.append(option)
    argv.append("--json")

    assert cli.main(argv) == 0
    assert calls == [probe_versions]
    assert json.loads(capsys.readouterr().out) == {"tools": []}


def test_software_text_lists_found_and_missing_tools(monkeypatch, capsys):
    profile = SimpleNamespace(tools=[
        SimpleNamespace(
            name="git",
            executable_path=r"C:\tools\git.exe",
            version="2.4.0",
            version_status=SimpleNamespace(value="detected"),
            message="Version detected",
        ),
        SimpleNamespace(
            name="ollama",
            executable_path=None,
            version=None,
            version_status=SimpleNamespace(value="not_found"),
            message="Command not found on PATH",
        ),
    ])
    monkeypatch.setattr(cli.Hestia, "detect_software", lambda **_: profile)

    assert cli.main(["software"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "Configured software (2 tools):",
        "",
        "- git",
        "  Status: Detected",
        r"  Path: C:\tools\git.exe",
        "  Version: 2.4.0",
        "  Message: Version detected",
        "",
        "- ollama",
        "  Status: Not Found",
        "  Path: not found",
        "  Message: Command not found on PATH",
    ]


def test_models_json_outputs_serialized_catalog(monkeypatch, capsys):
    models = [_profile({"accelerator": "none", "size": "tiny"})]
    calls = []

    def get_model_info(accelerator=None, size=None):
        calls.append((accelerator, size))
        return models

    monkeypatch.setattr(cli.Hestia, "get_model_info", get_model_info)

    assert cli.main(["models", "--json"]) == 0
    assert calls == [(None, None)]
    assert json.loads(capsys.readouterr().out) == [
        {"accelerator": "none", "size": "tiny"}
    ]


@pytest.mark.parametrize(
    ("options", "expected"),
    [
        (["--accelerator", "nvidia_cuda"], (AcceleratorType.NVIDIA_CUDA, None)),
        (["--size", "medium"], (None, ModelSize.MEDIUM)),
        (
            ["--accelerator", "amd_rocm", "--size", "large"],
            (AcceleratorType.AMD_ROCM, ModelSize.LARGE),
        ),
    ],
)
def test_models_passes_optional_filters(monkeypatch, options, expected):
    calls = []
    monkeypatch.setattr(
        cli.Hestia,
        "get_model_info",
        lambda accelerator=None, size=None: calls.append((accelerator, size)) or [],
    )

    assert cli.main(["models", *options]) == 0
    assert calls == [expected]


def test_models_text_lists_catalog_entries(monkeypatch, capsys):
    model = SimpleNamespace(
        accelerator=SimpleNamespace(value="nvidia_cuda"),
        size=SimpleNamespace(value="small"),
        categories={"models": ["example:small", "another:small"], "thinking": []},
        quantization="q4_k_m",
        batch_size=2,
        context=8192,
        performance="Fast",
    )
    monkeypatch.setattr(cli.Hestia, "get_model_info", lambda *_: [model])

    assert cli.main(["models"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "Model catalog (1 entry):",
        "",
        "[1] nvidia_cuda / small",
        "    Quantization: q4_k_m",
        "    Batch size: 2",
        "    Context: 8,192 tokens",
        "    Performance: Fast",
        "    Models by category:",
        "      General:",
        "        - example:small",
        "        - another:small",
    ]


def test_recommend_json_uses_detected_profile(monkeypatch, capsys):
    profile = _profile({"cpu_brand": "Example CPU"})
    recommendation = _profile({"model_size": "small"})
    calls = []
    monkeypatch.setattr(cli.Hestia, "detect_hardware", lambda: profile)
    monkeypatch.setattr(
        cli.Hestia, "recommend_model",
        lambda value: calls.append(value) or recommendation,
    )

    assert cli.main(["recommend", "--json"]) == 0
    assert calls == [profile]
    assert json.loads(capsys.readouterr().out) == {"model_size": "small"}


def test_report_json_combines_hardware_and_recommendation(monkeypatch, capsys):
    profile = _profile({"cpu_brand": "Example CPU"})
    recommendation = _profile({"model_size": "small"})
    monkeypatch.setattr(cli.Hestia, "detect_hardware", lambda: profile)
    monkeypatch.setattr(cli.Hestia, "recommend_model", lambda _: recommendation)

    assert cli.main(["report", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "hardware": {"cpu_brand": "Example CPU"},
        "recommendation": {"model_size": "small"},
    }


def test_report_text_uses_public_hardware_report(monkeypatch, capsys):
    profile = _profile({})
    recommendation = _profile({})
    calls = []
    monkeypatch.setattr(cli.Hestia, "detect_hardware", lambda: profile)
    monkeypatch.setattr(cli.Hestia, "recommend_model", lambda _: recommendation)
    monkeypatch.setattr(
        cli.Hestia, "print_hardware_report",
        lambda *args: calls.append(args),
    )

    assert cli.main(["report"]) == 0
    assert calls == [(profile, recommendation)]
    assert capsys.readouterr().out == ""


def test_scan_json_combines_profiles_and_disables_probes(monkeypatch, capsys):
    hardware = _profile({"cpu_brand": "Example CPU"})
    software = _profile({"tools": []})
    calls = []
    monkeypatch.setattr(cli.Hestia, "detect_hardware", lambda: hardware)
    monkeypatch.setattr(
        cli.Hestia, "detect_software",
        lambda *, probe_versions: calls.append(probe_versions) or software,
    )

    assert cli.main(["scan", "--no-version-probes", "--json"]) == 0
    assert calls == [False]
    assert json.loads(capsys.readouterr().out) == {
        "hardware": {"cpu_brand": "Example CPU"},
        "software": {"tools": []},
    }


def test_scan_text_uses_hardware_report_and_lists_software(monkeypatch, capsys):
    hardware = _profile({})
    software = SimpleNamespace(tools=[])
    reports = []
    monkeypatch.setattr(cli.Hestia, "detect_hardware", lambda: hardware)
    monkeypatch.setattr(cli.Hestia, "detect_software", lambda **_: software)
    monkeypatch.setattr(cli.Hestia, "print_hardware_report", lambda profile: reports.append(profile))

    assert cli.main(["scan", "--no-version-probes"]) == 0
    assert reports == [hardware]
    assert capsys.readouterr().out.splitlines() == [
        "Configured software (0 tools):",
        "  No configured tools.",
    ]


def test_detection_errors_are_not_suppressed(monkeypatch):
    def fail_detection():
        raise RuntimeError("detection failed")

    monkeypatch.setattr(cli.Hestia, "detect_hardware", fail_detection)

    with pytest.raises(RuntimeError, match="detection failed"):
        cli.main(["hardware", "--json"])


def test_unknown_command_is_rejected(capsys):
    with pytest.raises(SystemExit) as error:
        cli.main(["unknown"])

    assert error.value.code == 2
    assert "invalid choice" in capsys.readouterr().err
