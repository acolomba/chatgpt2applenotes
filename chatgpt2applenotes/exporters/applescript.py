"""AppleScript operations for Apple Notes integration."""

import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class NoteInfo:
    """metadata for an existing Apple Note."""

    note_id: str
    conversation_id: str
    last_message_id: str


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


def list_note_ids(folder: str) -> list[str]:
    """
    lists all note IDs in folder.

    Args:
        folder: Apple Notes folder name (supports "Parent/Child" format)

    Returns:
        list of note IDs (x-coredata://... format)
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
        set result to result & (id of aNote) & linefeed
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
        return [line for line in output.split("\n") if line]
    except subprocess.CalledProcessError:
        return []


def read_note_body_by_id(note_id: str) -> Optional[str]:
    """
    reads note body by direct ID lookup.

    Args:
        note_id: Apple Notes internal ID (x-coredata://... format)

    Returns:
        note body HTML if found, None otherwise
    """
    id_escaped = _escape_applescript(note_id)

    applescript = f"""
tell application "Notes"
    try
        set theNote to note id "{id_escaped}"
        return body of theNote
    on error
        return ""
    end try
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


def write_note(
    folder_name: str,
    conversation_id: str,
    html_content: str,
    overwrite: bool,
    image_files: list[str],
) -> None:
    """
    writes or updates note in Apple Notes using AppleScript.

    Args:
        folder_name: folder to store the note in
        conversation_id: conversation ID for finding existing notes
        html_content: HTML content for the note
        overwrite: if True, update existing note with same ID
        image_files: list of image file paths to add as attachments
    """
    # writes HTML to temporary file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as html_file:
        html_file.write(html_content)
        html_path = html_file.name

    # escapes quotes and backslashes for AppleScript
    html_path_escaped = _escape_applescript(html_path)
    id_escaped = _escape_applescript(conversation_id)

    # gets folder reference and creation script (handles nested folders)
    folder_ref = get_folder_ref(folder_name)
    folder_create = get_folder_create_script(folder_name)

    # prepares image attachment commands with deduplication
    # workaround for Apple Notes 4.10-4.11 bug that creates duplicate attachments
    attachment_commands = ""
    if image_files:
        attachment_commands = """
    set attachmentsAdded to 0
"""
        for idx, img_path in enumerate(image_files):
            img_path_escaped = _escape_applescript(img_path)
            attachment_commands += f"""
    set imgFile{idx} to POSIX file "{img_path_escaped}"
    make new attachment at theNote with data imgFile{idx}
    set attachmentsAdded to attachmentsAdded + 1
    if ((count attachments of theNote) > attachmentsAdded) then
        delete last attachment of theNote
    end if
"""

    if overwrite:
        # tries to find and delete existing note, then creates new one
        applescript = f"""
tell application "Notes"
    -- creates folder if it doesn't exist
{folder_create}

    set targetFolder to {folder_ref}

    -- searches for and deletes existing note containing conversation ID
    set notesList to every note of targetFolder
    repeat with aNote in notesList
        if body of aNote contains "{id_escaped}" then
            delete aNote
            exit repeat
        end if
    end repeat

    -- reads HTML from file
    set htmlContent to read POSIX file "{html_path_escaped}" as «class utf8»

    -- creates new note (title derived from H1 heading)
    set theNote to make new note at targetFolder with properties {{body:htmlContent}}

    -- adds image attachments (with deduplication for Apple Notes 4.10-4.11 bug)
{attachment_commands}
end tell
"""
    else:
        # creates new note without checking for existing
        applescript = f"""
tell application "Notes"
    -- creates folder if it doesn't exist
{folder_create}

    -- reads HTML from file
    set htmlContent to read POSIX file "{html_path_escaped}" as «class utf8»

    -- creates note (title derived from H1 heading)
    set theNote to make new note at {folder_ref} with properties {{body:htmlContent}}

    -- adds image attachments (with deduplication for Apple Notes 4.10-4.11 bug)
{attachment_commands}
end tell
"""

    # executes AppleScript via temporary file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".scpt", delete=False
    ) as script_file:
        script_file.write(applescript)
        script_path = script_file.name

    try:
        subprocess.run(
            ["osascript", script_path],
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        # cleans up temporary files
        Path(script_path).unlink(missing_ok=True)
        Path(html_path).unlink(missing_ok=True)
        # cleans up image files
        for img_path in image_files:
            Path(img_path).unlink(missing_ok=True)
