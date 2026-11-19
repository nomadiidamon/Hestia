"""@example software_04_detection.py

Discover the configured software catalog without running version commands.
"""

from Hestia.software import detect_software


def main() -> None:
    profile = detect_software(probe_versions=False)
    print("Configured software on PATH (version probes disabled)")
    for tool in profile.tools:
        path = tool.executable_path or "not found"
        print(f"- {tool.name}: {path}; {tool.version_status.value}")


if __name__ == "__main__":
    main()
