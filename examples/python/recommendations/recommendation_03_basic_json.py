"""@example recommendation_03_basic_json.py
Serialize detected hardware and its model recommendation.
"""

import json
import Hestia

profile = Hestia.detect_hardware()
recommendation = Hestia.recommend_model(profile)
print(json.dumps({"hardware": profile.to_dict(), "recommendation": recommendation.to_dict()}, indent=2))