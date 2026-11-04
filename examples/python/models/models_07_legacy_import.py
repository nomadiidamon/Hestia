"""@example models_07_legacy_import.py

The old import path still works."""

from Hestia.model_catalog import MODEL_DATABASE as legacy
from Hestia.models import MODEL_DATABASE

print(legacy is MODEL_DATABASE)
