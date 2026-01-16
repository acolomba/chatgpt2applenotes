"""AppleScript operations for Apple Notes integration."""

from typing import Optional


def _parse_folder_path(folder_name: str) -> tuple[str, Optional[str]]:
    """parses folder path into (parent, subfolder) where subfolder is None for flat paths."""
    if "/" in folder_name:
        parts = folder_name.split("/", 1)
        return parts[0], parts[1]
    return folder_name, None


def _escape_applescript(value: str) -> str:
    """escapes string for embedding in AppleScript."""
    return value.replace("\\", "\\\\").replace('"', '\\"')
