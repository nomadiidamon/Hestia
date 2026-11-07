"""@example hardware_02_report.py
Print a hardware report without requiring an accelerator.
"""

import Hestia


profile = Hestia.detect_hardware()
Hestia.print_hardware_report(profile)