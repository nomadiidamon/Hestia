"""@example recommendation_01_basic.py
Pair a hardware profile with advisory model catalog recommendations.
"""

import Hestia


profile = Hestia.detect_hardware()
recommendation = Hestia.recommend_model(profile)
Hestia.print_hardware_report(profile, recommendation)