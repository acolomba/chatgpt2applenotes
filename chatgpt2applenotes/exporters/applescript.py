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


def get_folder_ref(folder_name: str) -> str:
    """
    generates AppleScript folder reference for given path.

    Args:
        folder_name: folder path like "Folder" or "Parent/Child"

    Returns:
        AppleScript folder reference like 'folder "Folder"' or
        'folder "Child" of folder "Parent"'
    """
    parent, subfolder = _parse_folder_path(folder_name)
    parent_escaped = _escape_applescript(parent)
    if subfolder:
        subfolder_escaped = _escape_applescript(subfolder)
        return f'folder "{subfolder_escaped}" of folder "{parent_escaped}"'
    return f'folder "{parent_escaped}"'


def get_folder_create_script(folder_name: str) -> str:
    """
    generates AppleScript to create folder (and parent if nested).

    Args:
        folder_name: folder path like "Folder" or "Parent/Child"

    Returns:
        AppleScript snippet to create the folder structure
    """
    parent, subfolder = _parse_folder_path(folder_name)
    parent_escaped = _escape_applescript(parent)

    if subfolder:
        subfolder_escaped = _escape_applescript(subfolder)
        return f"""
    if not (exists folder "{parent_escaped}") then
        make new folder with properties {{name:"{parent_escaped}"}}
    end if
    if not (exists folder "{subfolder_escaped}" of folder "{parent_escaped}") then
        make new folder at folder "{parent_escaped}" with properties {{name:"{subfolder_escaped}"}}
    end if"""
    return f"""
    if not (exists folder "{parent_escaped}") then
        make new folder with properties {{name:"{parent_escaped}"}}
    end if"""
