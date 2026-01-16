"""AppleScript operations for Apple Notes integration."""

import re
import subprocess
import tempfile
from pathlib import Path
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


def read_note_body(folder: str, conversation_id: str) -> Optional[str]:
    """
    reads note body from Apple Notes by conversation ID.

    Args:
        folder: Apple Notes folder name (supports "Parent/Child" format)
        conversation_id: conversation ID to search for

    Returns:
        note body HTML if found, None otherwise
    """
    folder_ref = get_folder_ref(folder)
    id_escaped = _escape_applescript(conversation_id)

    applescript = f"""
tell application "Notes"
    if not (exists {folder_ref}) then
        return ""
    end if

    set notesList to every note of {folder_ref}
    repeat with aNote in notesList
        if body of aNote contains "{id_escaped}" then
            return body of aNote
        end if
    end repeat
    return ""
end tell
"""
    try:
        result = subprocess.run(
            ["osascript", "-e", applescript],
            check=True,
            capture_output=True,
            text=True,
        )
        body = result.stdout.strip()
        return body if body else None
    except subprocess.CalledProcessError:
        return None


def list_note_conversation_ids(folder: str) -> list[str]:
    """
    lists all conversation IDs from notes in folder.

    Args:
        folder: Apple Notes folder name (supports "Parent/Child" format)

    Returns:
        list of conversation IDs found in notes
    """
    folder_ref = get_folder_ref(folder)

    applescript = f"""
tell application "Notes"
    if not (exists {folder_ref}) then
        return ""
    end if

    set notesList to every note of {folder_ref}
    set result to ""
    repeat with aNote in notesList
        set result to result & (body of aNote) & "|||SEPARATOR|||"
    end repeat
    return result
end tell
"""
    try:
        result = subprocess.run(
            ["osascript", "-e", applescript],
            check=True,
            capture_output=True,
            text=True,
        )
        output = result.stdout.strip()
        if not output:
            return []

        # extracts conversation IDs from note bodies
        # looks for UUID-format conversation ID followed by colon in footer
        conv_ids = []
        for body in output.split("|||SEPARATOR|||"):
            # matches footer format: {conversation_id}:{message_id}
            match = re.search(
                r"([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}):",
                body,
            )
            if match:
                conv_ids.append(match.group(1))

        return conv_ids
    except subprocess.CalledProcessError:
        return []


def move_note_to_archive(folder: str, conversation_id: str) -> bool:
    """
    moves note to Archive subfolder.

    Args:
        folder: Apple Notes folder name (supports "Parent/Child" format)
        conversation_id: conversation ID to find and move

    Returns:
        True if successful, False otherwise
    """
    folder_ref = get_folder_ref(folder)
    id_escaped = _escape_applescript(conversation_id)

    applescript = f"""
tell application "Notes"
    if not (exists {folder_ref}) then
        return false
    end if

    -- creates Archive subfolder if needed
    if not (exists folder "Archive" of {folder_ref}) then
        make new folder at {folder_ref} with properties {{name:"Archive"}}
    end if

    set notesList to every note of {folder_ref}
    repeat with aNote in notesList
        if body of aNote contains "{id_escaped}" then
            move aNote to folder "Archive" of {folder_ref}
            return true
        end if
    end repeat
    return false
end tell
"""
    try:
        result = subprocess.run(
            ["osascript", "-e", applescript],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() == "true"
    except subprocess.CalledProcessError:
        return False


def append_to_note(folder: str, conversation_id: str, html_content: str) -> bool:
    """
    appends HTML content to existing note.

    Args:
        folder: Apple Notes folder name (supports "Parent/Child" format)
        conversation_id: conversation ID to find
        html_content: HTML to append

    Returns:
        True if successful, False otherwise
    """
    folder_ref = get_folder_ref(folder)
    id_escaped = _escape_applescript(conversation_id)

    # writes HTML to temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as html_file:
        html_file.write(html_content)
        html_path = html_file.name

    html_path_escaped = _escape_applescript(html_path)

    applescript = f"""
tell application "Notes"
    if not (exists {folder_ref}) then
        return false
    end if

    set htmlContent to read POSIX file "{html_path_escaped}" as «class utf8»

    set notesList to every note of {folder_ref}
    repeat with aNote in notesList
        if body of aNote contains "{id_escaped}" then
            set oldBody to body of aNote
            set body of aNote to oldBody & htmlContent
            return true
        end if
    end repeat
    return false
end tell
"""
    try:
        result = subprocess.run(
            ["osascript", "-e", applescript],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() == "true"
    except subprocess.CalledProcessError:
        return False
    finally:
        Path(html_path).unlink(missing_ok=True)
