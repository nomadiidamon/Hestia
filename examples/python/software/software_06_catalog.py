"""@example software_06_catalog.py

Define a caller-owned catalog entry and detect its configured command.
"""

import re

from Hestia.software import SoftwareDefinition, detect_software


def parse_git_version(output: str) -> str | None:
    match = re.search(r"(?m)^git version\s+(\S+)", output)
    return match.group(1) if match else None


def detect_custom_catalog():
    catalog = (
        SoftwareDefinition(
            name="git",
            executables=("git",),
            version_args=("--version",),
            version_parser=parse_git_version,
        ),
    )
    return detect_software(catalog)


def main() -> None:
    profile = detect_custom_catalog()
    for tool in profile.tools:
        print(f"{tool.name}: {tool.version or tool.version_status.value} ({tool.message})")


if __name__ == "__main__":
    main()
