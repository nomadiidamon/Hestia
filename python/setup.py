"""Reads shared metadata from ../project.ini (the single source of truth)."""
import configparser
import re
from pathlib import Path

from setuptools import setup

INI = Path(__file__).resolve().parent.parent / "project.ini"

cfg = configparser.ConfigParser()
cfg.read(INI, encoding="utf-8")
project = cfg["project"]

people = [p.strip() for p in cfg["contributors"]["maintainers"].split(",") if p.strip()]
names = [re.sub(r"\s*<.*>$", "", p) for p in people]
emails = [m.group(1) for p in people if (m := re.search(r"<(.*)>$", p))]

setup(
    version=project["version"],
    description=project["description"].strip('"'),
    long_description=(INI.parent / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    license=project["license"],
    python_requires=cfg["compatibility"]["python_requires"],
    author=", ".join(names),
    author_email=", ".join(emails) or None,
    project_urls={"Homepage": project["homepage"]},
)
