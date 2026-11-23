"""Terminal styling shared by human-readable reports."""

from Auctor.Stylus.Colors import Style
from Auctor.Stylus.TTY import TTY


def styled(text: str, *codes: str) -> str:
    return Style(text, *codes) if TTY().supports_color() else text