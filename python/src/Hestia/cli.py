"""Command-line interface for Hestia."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import Hestia

if TYPE_CHECKING:
    from Hestia.models import ModelInfo
    from Hestia.software import SoftwareProfile


def _add_json_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="write machine-readable JSON")


def _add_probe_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--no-version-probes",
        action="store_true",
        help="discover configured software without running version commands",
    )


def _write_json(value: Any) -> None:
    print(json.dumps(value, indent=2, allow_nan=False))


def _category_label(name: str) -> str:
    labels = {
        "models": "General",
        "thinking": "Thinking",
        "tools": "Tool use",
        "vision": "Vision",
    }
    return labels.get(name, name.replace("_", " ").title())


def _print_software(profile: SoftwareProfile) -> None:
    print(f"Configured software ({len(profile.tools)} tools):")
    if not profile.tools:
        print("  No configured tools.")
        return

    for tool in profile.tools:
        status = tool.version_status.value.replace("_", " ").title()
        print(f"\n- {tool.name}")
        print(f"  Status: {status}")
        print(f"  Path: {tool.executable_path or 'not found'}")
        if tool.version is not None:
            print(f"  Version: {tool.version}")
        print(f"  Message: {tool.message}")


def _print_models(models: list[ModelInfo]) -> None:
    count_label = "entry" if len(models) == 1 else "entries"
    print(f"Model catalog ({len(models)} {count_label}):")
    if not models:
        print("  No catalog entries.")
        return

    for index, model in enumerate(models, start=1):
        print(f"\n[{index}] {model.accelerator.value} / {model.size.value}")
        print(f"    Quantization: {model.quantization}")
        print(f"    Batch size: {model.batch_size}")
        print(f"    Context: {model.context:,} tokens")
        print(f"    Performance: {model.performance}")
        populated_categories = [
            (name, entries) for name, entries in model.categories.items() if entries
        ]
        if not populated_categories:
            print("    Models: none")
            continue

        print("    Models by category:")
        for name, entries in populated_categories:
            print(f"      {_category_label(name)}:")
            for entry in entries:
                print(f"        - {entry}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hestia", description="Inspect hardware and software capabilities.")
    parser.add_argument("--version", action="version", version=f"Hestia {Hestia.__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    scan = commands.add_parser("scan", help="scan hardware and configured software")
    _add_json_option(scan)
    _add_probe_option(scan)

    hardware = commands.add_parser("hardware", help="show the hardware profile")
    _add_json_option(hardware)

    software = commands.add_parser("software", help="show configured software on PATH")
    _add_json_option(software)
    _add_probe_option(software)

    models = commands.add_parser("models", help="list model catalog entries")
    _add_json_option(models)

    recommend = commands.add_parser("recommend", help="recommend models for this hardware")
    _add_json_option(recommend)

    report = commands.add_parser("report", help="show hardware and model recommendations")
    _add_json_option(report)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return its process exit code."""
    args = _build_parser().parse_args(argv)

    if args.command == "hardware":
        profile = Hestia.detect_hardware()
        if args.json:
            _write_json(profile.to_dict())
        else:
            Hestia.print_hardware_report(profile)
    elif args.command == "software":
        profile = Hestia.detect_software(probe_versions=not args.no_version_probes)
        if args.json:
            _write_json(profile.to_dict())
        else:
            _print_software(profile)
    elif args.command == "models":
        model_results = Hestia.get_model_info()
        models = model_results if isinstance(model_results, list) else [model_results]
        if args.json:
            _write_json([model.to_dict() for model in models])
        else:
            _print_models(models)
    elif args.command == "recommend":
        profile = Hestia.detect_hardware()
        recommendation = Hestia.recommend_model(profile)
        if args.json:
            _write_json(recommendation.to_dict())
        else:
            Hestia.print_hardware_report(profile, recommendation)
    elif args.command == "report":
        profile = Hestia.detect_hardware()
        recommendation = Hestia.recommend_model(profile)
        if args.json:
            _write_json({
                "hardware": profile.to_dict(),
                "recommendation": recommendation.to_dict(),
            })
        else:
            Hestia.print_hardware_report(profile, recommendation)
    elif args.command == "scan":
        hardware_profile = Hestia.detect_hardware()
        software_profile = Hestia.detect_software(probe_versions=not args.no_version_probes)
        if args.json:
            _write_json({
                "hardware": hardware_profile.to_dict(),
                "software": software_profile.to_dict(),
            })
        else:
            Hestia.print_hardware_report(hardware_profile)
            _print_software(software_profile)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
