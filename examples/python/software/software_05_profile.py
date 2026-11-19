"""@example software_05_profile.py

Serialize a software profile as JSON-friendly data.
"""

import json

from Hestia.software import detect_software


def main() -> None:
    profile = detect_software(probe_versions=False)
    print(json.dumps(profile.to_dict(), indent=2))


if __name__ == "__main__":
    main()
