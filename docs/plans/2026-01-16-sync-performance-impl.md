# Sync Performance Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce sync time from O(N×M) to O(N+M) by scanning Apple Notes folder once upfront and using direct note ID lookups.

**Architecture:** Add `NoteInfo` dataclass to hold note metadata. Create two-phase scan (list IDs, then read bodies). Replace per-conversation folder scans with dict lookups. Use note IDs for direct operations.

**Tech Stack:** Python 3.14, AppleScript via subprocess, dataclasses

---

## Task 1: Add NoteInfo Dataclass

**Files:**

- Modify: `chatgpt2applenotes/exporters/applescript.py:1-10`
- Test: `tests/test_applescript.py` (new file)

Step 1. Write the failing test

Create `tests/test_applescript.py`:

```python
"""tests for AppleScript module."""

from chatgpt2applenotes.exporters.applescript import NoteInfo


def test_noteinfo_creation():
    """tests NoteInfo dataclass holds note metadata."""
    info = NoteInfo(
        note_id="x-coredata://123",
        conversation_id="conv-uuid-1",
        last_message_id="msg-uuid-a",
    )
    assert info.note_id == "x-coredata://123"
    assert info.conversation_id == "conv-uuid-1"
    assert info.last_message_id == "msg-uuid-a"
```

Step 2. Run test to verify it fails

Run: `uv run pytest tests/test_applescript.py::test_noteinfo_creation -v`

Expected: FAIL with "cannot import name 'NoteInfo'"

Step 3. Write minimal implementation

Add to top of `chatgpt2applenotes/exporters/applescript.py` after imports:

```python
from dataclasses import dataclass


@dataclass
class NoteInfo:
    """metadata for an existing Apple Note."""

    note_id: str
    conversation_id: str
    last_message_id: str
```

Step 4. Run test to verify it passes

Run: `uv run pytest tests/test_applescript.py::test_noteinfo_creation -v`

Expected: PASS

Step 5. Commit

```bash
git add chatgpt2applenotes/exporters/applescript.py tests/test_applescript.py
git commit -m "feat: add NoteInfo dataclass for note metadata"
```

---

## Task 2: Add list_note_ids Function

**Files:**

- Modify: `chatgpt2applenotes/exporters/applescript.py`
- Test: `tests/test_applescript.py`

Step 1. Write the failing test

Add to `tests/test_applescript.py`:

```python
from unittest.mock import patch, MagicMock
import subprocess

from chatgpt2applenotes.exporters.applescript import list_note_ids


def test_list_note_ids_returns_ids():
    """tests list_note_ids parses AppleScript output."""
    mock_result = MagicMock()
    mock_result.stdout = "x-coredata://id1\nx-coredata://id2\nx-coredata://id3\n"

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        result = list_note_ids("TestFolder")

    assert result == ["x-coredata://id1", "x-coredata://id2", "x-coredata://id3"]
    mock_run.assert_called_once()


def test_list_note_ids_returns_empty_on_error():
    """tests list_note_ids returns empty list on AppleScript error."""
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "osascript")):
        result = list_note_ids("TestFolder")

    assert result == []


def test_list_note_ids_returns_empty_for_empty_folder():
    """tests list_note_ids returns empty list for empty folder."""
    mock_result = MagicMock()
    mock_result.stdout = ""

    with patch("subprocess.run", return_value=mock_result):
        result = list_note_ids("TestFolder")

    assert result == []
```

Step 2. Run test to verify it fails

Run: `uv run pytest tests/test_applescript.py::test_list_note_ids_returns_ids -v`

Expected: FAIL with "cannot import name 'list_note_ids'"

Step 3. Write minimal implementation

Add to `chatgpt2applenotes/exporters/applescript.py`:

```python
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
```

Step 4. Run tests to verify they pass

Run: `uv run pytest tests/test_applescript.py -k "list_note_ids" -v`

Expected: 3 PASS

Step 5. Commit

```bash
git add chatgpt2applenotes/exporters/applescript.py tests/test_applescript.py
git commit -m "feat: add list_note_ids function for folder scanning"
```

---

## Task 3: Add read_note_body_by_id Function

**Files:**

- Modify: `chatgpt2applenotes/exporters/applescript.py`
- Test: `tests/test_applescript.py`

Step 1. Write the failing test

Add to `tests/test_applescript.py`:

```python
from chatgpt2applenotes.exporters.applescript import read_note_body_by_id


def test_read_note_body_by_id_returns_body():
    """tests read_note_body_by_id returns note body."""
    mock_result = MagicMock()
    mock_result.stdout = "<html><body>Note content</body></html>"

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        result = read_note_body_by_id("x-coredata://123")

    assert result == "<html><body>Note content</body></html>"
    mock_run.assert_called_once()


def test_read_note_body_by_id_returns_none_on_error():
    """tests read_note_body_by_id returns None on error."""
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "osascript")):
        result = read_note_body_by_id("x-coredata://123")

    assert result is None


def test_read_note_body_by_id_returns_none_for_empty():
    """tests read_note_body_by_id returns None for empty body."""
    mock_result = MagicMock()
    mock_result.stdout = ""

    with patch("subprocess.run", return_value=mock_result):
        result = read_note_body_by_id("x-coredata://123")

    assert result is None
```

Step 2. Run test to verify it fails

Run: `uv run pytest tests/test_applescript.py::test_read_note_body_by_id_returns_body -v`

Expected: FAIL with "cannot import name 'read_note_body_by_id'"

Step 3. Write minimal implementation

Add to `chatgpt2applenotes/exporters/applescript.py`:

```python
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
```

Step 4. Run tests to verify they pass

Run: `uv run pytest tests/test_applescript.py -k "read_note_body_by_id" -v`

Expected: 3 PASS

Step 5. Commit

```bash
git add chatgpt2applenotes/exporters/applescript.py tests/test_applescript.py
git commit -m "feat: add read_note_body_by_id for direct note lookup"
```

---

## Task 4: Add scan_folder_notes Function

**Files:**

- Modify: `chatgpt2applenotes/exporters/applescript.py`
- Test: `tests/test_applescript.py`

Step 1. Write the failing test

Add to `tests/test_applescript.py`:

```python
from chatgpt2applenotes.exporters.applescript import scan_folder_notes, NoteInfo


def test_scan_folder_notes_builds_index():
    """tests scan_folder_notes builds conversation_id -> NoteInfo index."""
    # mock list_note_ids to return 2 note IDs
    # mock read_note_body_by_id to return bodies with footer metadata

    body1 = '<html>Content 1<p style="color:gray">conv-uuid-1:msg-uuid-a</p></html>'
    body2 = '<html>Content 2<p style="color:gray">conv-uuid-2:msg-uuid-b</p></html>'

    with patch(
        "chatgpt2applenotes.exporters.applescript.list_note_ids",
        return_value=["x-coredata://id1", "x-coredata://id2"],
    ):
        with patch(
            "chatgpt2applenotes.exporters.applescript.read_note_body_by_id",
            side_effect=[body1, body2],
        ):
            result = scan_folder_notes("TestFolder")

    assert len(result) == 2
    assert "conv-uuid-1" in result
    assert "conv-uuid-2" in result
    assert result["conv-uuid-1"].note_id == "x-coredata://id1"
    assert result["conv-uuid-1"].last_message_id == "msg-uuid-a"
    assert result["conv-uuid-2"].note_id == "x-coredata://id2"
    assert result["conv-uuid-2"].last_message_id == "msg-uuid-b"


def test_scan_folder_notes_skips_notes_without_footer():
    """tests scan_folder_notes skips notes without valid footer."""
    body1 = "<html>Content without footer</html>"
    body2 = '<html>Content 2<p style="color:gray">conv-uuid-2:msg-uuid-b</p></html>'

    with patch(
        "chatgpt2applenotes.exporters.applescript.list_note_ids",
        return_value=["x-coredata://id1", "x-coredata://id2"],
    ):
        with patch(
            "chatgpt2applenotes.exporters.applescript.read_note_body_by_id",
            side_effect=[body1, body2],
        ):
            result = scan_folder_notes("TestFolder")

    assert len(result) == 1
    assert "conv-uuid-2" in result


def test_scan_folder_notes_returns_empty_for_empty_folder():
    """tests scan_folder_notes returns empty dict for empty folder."""
    with patch(
        "chatgpt2applenotes.exporters.applescript.list_note_ids",
        return_value=[],
    ):
        result = scan_folder_notes("TestFolder")

    assert result == {}
```

Step 2. Run test to verify it fails

Run: `uv run pytest tests/test_applescript.py::test_scan_folder_notes_builds_index -v`

Expected: FAIL with "cannot import name 'scan_folder_notes'"

Step 3. Write minimal implementation

Add to `chatgpt2applenotes/exporters/applescript.py`:

```python
def scan_folder_notes(folder: str) -> dict[str, NoteInfo]:
    """
    scans folder and builds conversation_id -> NoteInfo index.

    Args:
        folder: Apple Notes folder name (supports "Parent/Child" format)

    Returns:
        dict mapping conversation_id to NoteInfo
    """
    note_ids = list_note_ids(folder)
    index: dict[str, NoteInfo] = {}

    for note_id in note_ids:
        body = read_note_body_by_id(note_id)
        if body:
            # extracts conversation_id:last_message_id from footer
            match = re.search(
                r"([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}):"
                r"([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})",
                body,
            )
            if match:
                conv_id = match.group(1)
                msg_id = match.group(2)
                index[conv_id] = NoteInfo(note_id, conv_id, msg_id)

    return index
```

Step 4. Run tests to verify they pass

Run: `uv run pytest tests/test_applescript.py -k "scan_folder_notes" -v`

Expected: 3 PASS

Step 5. Commit

```bash
git add chatgpt2applenotes/exporters/applescript.py tests/test_applescript.py
git commit -m "feat: add scan_folder_notes for single-pass folder indexing"
```

---

## Task 5: Add delete_note_by_id Function

**Files:**

- Modify: `chatgpt2applenotes/exporters/applescript.py`
- Test: `tests/test_applescript.py`

Step 1. Write the failing test

Add to `tests/test_applescript.py`:

```python
from chatgpt2applenotes.exporters.applescript import delete_note_by_id


def test_delete_note_by_id_returns_true_on_success():
    """tests delete_note_by_id returns True on success."""
    mock_result = MagicMock()
    mock_result.stdout = ""

    with patch("subprocess.run", return_value=mock_result):
        result = delete_note_by_id("x-coredata://123")

    assert result is True


def test_delete_note_by_id_returns_false_on_error():
    """tests delete_note_by_id returns False on error."""
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "osascript")):
        result = delete_note_by_id("x-coredata://123")

    assert result is False
```

Step 2. Run test to verify it fails

Run: `uv run pytest tests/test_applescript.py::test_delete_note_by_id_returns_true_on_success -v`

Expected: FAIL with "cannot import name 'delete_note_by_id'"

Step 3. Write minimal implementation

Add to `chatgpt2applenotes/exporters/applescript.py`:

```python
def delete_note_by_id(note_id: str) -> bool:
    """
    deletes note by direct ID lookup.

    Args:
        note_id: Apple Notes internal ID (x-coredata://... format)

    Returns:
        True if successful, False otherwise
    """
    id_escaped = _escape_applescript(note_id)

    applescript = f"""
tell application "Notes"
    try
        delete note id "{id_escaped}"
        return true
    on error
        return false
    end try
end tell
"""
    try:
        subprocess.run(
            ["osascript", "-e", applescript],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False
```

Step 4. Run tests to verify they pass

Run: `uv run pytest tests/test_applescript.py -k "delete_note_by_id" -v`

Expected: 2 PASS

Step 5. Commit

```bash
git add chatgpt2applenotes/exporters/applescript.py tests/test_applescript.py
git commit -m "feat: add delete_note_by_id for direct note deletion"
```

---

## Task 6: Add move_note_to_archive_by_id Function

**Files:**

- Modify: `chatgpt2applenotes/exporters/applescript.py`
- Test: `tests/test_applescript.py`

Step 1. Write the failing test

Add to `tests/test_applescript.py`:

```python
from chatgpt2applenotes.exporters.applescript import move_note_to_archive_by_id


def test_move_note_to_archive_by_id_returns_true_on_success():
    """tests move_note_to_archive_by_id returns True on success."""
    mock_result = MagicMock()
    mock_result.stdout = "true"

    with patch("subprocess.run", return_value=mock_result):
        result = move_note_to_archive_by_id("x-coredata://123", "TestFolder")

    assert result is True


def test_move_note_to_archive_by_id_returns_false_on_error():
    """tests move_note_to_archive_by_id returns False on error."""
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "osascript")):
        result = move_note_to_archive_by_id("x-coredata://123", "TestFolder")

    assert result is False
```

Step 2. Run test to verify it fails

Run: `uv run pytest tests/test_applescript.py::test_move_note_to_archive_by_id_returns_true_on_success -v`

Expected: FAIL with "cannot import name 'move_note_to_archive_by_id'"

Step 3. Write minimal implementation

Add to `chatgpt2applenotes/exporters/applescript.py`:

```python
def move_note_to_archive_by_id(note_id: str, folder: str) -> bool:
    """
    moves note to Archive subfolder by direct ID lookup.

    Args:
        note_id: Apple Notes internal ID (x-coredata://... format)
        folder: Apple Notes folder name (supports "Parent/Child" format)

    Returns:
        True if successful, False otherwise
    """
    folder_ref = get_folder_ref(folder)
    id_escaped = _escape_applescript(note_id)

    applescript = f"""
tell application "Notes"
    try
        set theNote to note id "{id_escaped}"

        -- creates Archive subfolder if needed
        if not (exists folder "Archive" of {folder_ref}) then
            make new folder at {folder_ref} with properties {{name:"Archive"}}
        end if

        move theNote to folder "Archive" of {folder_ref}
        return true
    on error
        return false
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
        return result.stdout.strip() == "true"
    except subprocess.CalledProcessError:
        return False
```

Step 4. Run tests to verify they pass

Run: `uv run pytest tests/test_applescript.py -k "move_note_to_archive_by_id" -v`

Expected: 2 PASS

Step 5. Commit

```bash
git add chatgpt2applenotes/exporters/applescript.py tests/test_applescript.py
git commit -m "feat: add move_note_to_archive_by_id for direct archive operation"
```

---

## Task 7: Add scan_folder_notes Method to AppleNotesExporter

**Files:**

- Modify: `chatgpt2applenotes/exporters/apple_notes.py`
- Test: `tests/test_apple_notes_exporter.py`

Step 1. Write the failing test

Add to `tests/test_apple_notes_exporter.py`:

```python
def test_scan_folder_notes_delegates_to_applescript(mocker):
    """tests scan_folder_notes calls applescript.scan_folder_notes."""
    mock_scan = mocker.patch(
        "chatgpt2applenotes.exporters.applescript.scan_folder_notes",
        return_value={"conv-1": mocker.MagicMock()},
    )

    exporter = AppleNotesExporter(target="notes")
    result = exporter.scan_folder_notes("TestFolder")

    mock_scan.assert_called_once_with("TestFolder")
    assert "conv-1" in result
```

Step 2. Run test to verify it fails

Run: `uv run pytest tests/test_apple_notes_exporter.py::test_scan_folder_notes_delegates_to_applescript -v`

Expected: FAIL with "has no attribute 'scan_folder_notes'"

Step 3. Write minimal implementation

Add to `chatgpt2applenotes/exporters/apple_notes.py`:

First, update the import at top:

```python
from chatgpt2applenotes.exporters import applescript
from chatgpt2applenotes.exporters.applescript import NoteInfo
```

Then add method to `AppleNotesExporter` class:

```python
def scan_folder_notes(self, folder: str) -> dict[str, NoteInfo]:
    """scans folder and builds conversation_id -> NoteInfo index."""
    return applescript.scan_folder_notes(folder)
```

Step 4. Run test to verify it passes

Run: `uv run pytest tests/test_apple_notes_exporter.py::test_scan_folder_notes_delegates_to_applescript -v`

Expected: PASS

Step 5. Commit

```bash
git add chatgpt2applenotes/exporters/apple_notes.py tests/test_apple_notes_exporter.py
git commit -m "feat: add scan_folder_notes method to AppleNotesExporter"
```

---

## Task 8: Add move_note_to_archive_by_id Method to AppleNotesExporter

**Files:**

- Modify: `chatgpt2applenotes/exporters/apple_notes.py`
- Test: `tests/test_apple_notes_exporter.py`

Step 1. Write the failing test

Add to `tests/test_apple_notes_exporter.py`:

```python
def test_move_note_to_archive_by_id_delegates_to_applescript(mocker):
    """tests move_note_to_archive_by_id calls applescript function."""
    mock_move = mocker.patch(
        "chatgpt2applenotes.exporters.applescript.move_note_to_archive_by_id",
        return_value=True,
    )

    exporter = AppleNotesExporter(target="notes")
    result = exporter.move_note_to_archive_by_id("x-coredata://123", "TestFolder")

    mock_move.assert_called_once_with("x-coredata://123", "TestFolder")
    assert result is True
```

Step 2. Run test to verify it fails

Run: `uv run pytest tests/test_apple_notes_exporter.py::test_move_note_to_archive_by_id_delegates_to_applescript -v`

Expected: FAIL with "has no attribute 'move_note_to_archive_by_id'"

Step 3. Write minimal implementation

Add to `AppleNotesExporter` class in `chatgpt2applenotes/exporters/apple_notes.py`:

```python
def move_note_to_archive_by_id(self, note_id: str, folder: str) -> bool:
    """moves note to Archive subfolder by direct ID lookup."""
    return applescript.move_note_to_archive_by_id(note_id, folder)
```

Step 4. Run test to verify it passes

Run: `uv run pytest tests/test_apple_notes_exporter.py::test_move_note_to_archive_by_id_delegates_to_applescript -v`

Expected: PASS

Step 5. Commit

```bash
git add chatgpt2applenotes/exporters/apple_notes.py tests/test_apple_notes_exporter.py
git commit -m "feat: add move_note_to_archive_by_id method to AppleNotesExporter"
```

---

## Task 9: Update export Method to Accept existing Parameter

**Files:**

- Modify: `chatgpt2applenotes/exporters/apple_notes.py`
- Test: `tests/test_apple_notes_exporter.py`

Step 1. Write the failing test

Add to `tests/test_apple_notes_exporter.py`:

```python
from chatgpt2applenotes.exporters.applescript import NoteInfo


def test_export_uses_existing_noteinfo_for_update(mocker, tmp_path):
    """tests export uses existing NoteInfo to skip folder scan."""
    # creates a conversation
    conversation = Conversation(
        id="conv-123",
        title="Test",
        create_time=1234567890.0,
        messages=[
            Message(
                id="msg-new",
                author={"role": "user"},
                create_time=1234567891.0,
                content={"content_type": "text", "parts": ["New message"]},
            )
        ],
    )

    existing = NoteInfo(
        note_id="x-coredata://existing",
        conversation_id="conv-123",
        last_message_id="msg-old",
    )

    # mocks the applescript functions
    mock_delete = mocker.patch(
        "chatgpt2applenotes.exporters.applescript.delete_note_by_id",
        return_value=True,
    )
    mock_write = mocker.patch(
        "chatgpt2applenotes.exporters.applescript.write_note",
    )

    exporter = AppleNotesExporter(target="notes")
    exporter.export(
        conversation=conversation,
        destination="TestFolder",
        overwrite=True,
        existing=existing,
    )

    # should delete by ID, not scan folder
    mock_delete.assert_called_once_with("x-coredata://existing")
    mock_write.assert_called_once()
```

Step 2. Run test to verify it fails

Run: `uv run pytest tests/test_apple_notes_exporter.py::test_export_uses_existing_noteinfo_for_update -v`

Expected: FAIL with "unexpected keyword argument 'existing'"

Step 3. Write minimal implementation

Modify `export` method signature in `chatgpt2applenotes/exporters/apple_notes.py`:

```python
def export(
    self,
    conversation: Conversation,
    destination: str,
    dry_run: bool = False,
    overwrite: bool = True,
    existing: Optional[NoteInfo] = None,
) -> None:
```

Update the `_export_to_notes` call:

```python
if self.target == "notes":
    self._export_to_notes(conversation, destination, dry_run, overwrite, existing)
```

Update `_export_to_notes` signature and implementation:

```python
def _export_to_notes(
    self,
    conversation: Conversation,
    folder_name: str,
    dry_run: bool,
    overwrite: bool,
    existing: Optional[NoteInfo] = None,
) -> None:
    """exports conversation directly to Apple Notes."""
    if dry_run:
        print(f"Would write note '{conversation.title}' to folder '{folder_name}'")
        return

    # uses existing NoteInfo if provided, otherwise scan for note
    if existing:
        existing_body = applescript.read_note_body_by_id(existing.note_id)
        last_synced = existing.last_message_id
    else:
        existing_body = self.read_note_body(folder_name, conversation.id)
        last_synced = self.extract_last_synced_id(existing_body) if existing_body else None

    if existing_body and not overwrite:
        # tries append-only sync
        if last_synced:
            # finds new messages and appends
            append_html = self.generate_append_html(conversation, last_synced)
            if append_html:
                if self.append_to_note(folder_name, conversation.id, append_html):
                    return
                # falls through to overwrite if append fails
            else:
                # no new messages
                return

        # no sync marker found - fall back to overwrite
        overwrite = True

    # collects images and generates HTML content
    image_files: list[str] = []
    html_content = self._generate_html_with_images(conversation, image_files)

    # saves copy to cc_dir if configured
    if self.cc_dir:
        self._save_cc_copy(conversation, html_content)

    # deletes existing note by ID if we have it
    if existing and overwrite:
        applescript.delete_note_by_id(existing.note_id)

    # uses AppleScript to create note (always create new after delete)
    self._write_to_apple_notes(
        conversation, html_content, folder_name, overwrite and not existing, image_files
    )
```

Step 4. Run tests to verify they pass

Run: `uv run pytest tests/test_apple_notes_exporter.py -v`

Expected: All PASS

Step 5. Commit

```bash
git add chatgpt2applenotes/exporters/apple_notes.py tests/test_apple_notes_exporter.py
git commit -m "feat: add existing parameter to export for direct note updates"
```

---

## Task 10: Update sync_conversations to Use Single-Pass Scan

**Files:**

- Modify: `chatgpt2applenotes/sync.py`
- Test: `tests/test_sync.py`

Step 1. Write the failing test

Add to `tests/test_sync.py`:

```python
from chatgpt2applenotes.exporters.applescript import NoteInfo


def test_sync_scans_folder_once(mocker, tmp_path):
    """tests sync_conversations scans folder once upfront."""
    # creates test JSON file
    json_file = tmp_path / "conv1.json"
    json_file.write_text(
        '{"id": "conv-1", "title": "Test", "create_time": 1234567890, '
        '"mapping": {"node1": {"message": {"id": "msg-1", "author": {"role": "user"}, '
        '"create_time": 1234567890, "content": {"content_type": "text", "parts": ["Hi"]}}}}}'
    )

    # mocks the exporter methods
    mock_scan = mocker.patch(
        "chatgpt2applenotes.exporters.apple_notes.AppleNotesExporter.scan_folder_notes",
        return_value={},
    )
    mock_export = mocker.patch(
        "chatgpt2applenotes.exporters.apple_notes.AppleNotesExporter.export",
    )

    from chatgpt2applenotes.sync import sync_conversations

    sync_conversations(tmp_path, "TestFolder")

    # scan_folder_notes should be called exactly once
    mock_scan.assert_called_once_with("TestFolder")
    # export should be called with existing=None (no existing note)
    mock_export.assert_called_once()
    call_kwargs = mock_export.call_args.kwargs
    assert call_kwargs.get("existing") is None


def test_sync_passes_existing_noteinfo_to_export(mocker, tmp_path):
    """tests sync_conversations passes existing NoteInfo to export."""
    # creates test JSON file
    json_file = tmp_path / "conv1.json"
    json_file.write_text(
        '{"id": "conv-1", "title": "Test", "create_time": 1234567890, '
        '"mapping": {"node1": {"message": {"id": "msg-1", "author": {"role": "user"}, '
        '"create_time": 1234567890, "content": {"content_type": "text", "parts": ["Hi"]}}}}}'
    )

    existing_note = NoteInfo(
        note_id="x-coredata://existing",
        conversation_id="conv-1",
        last_message_id="msg-old",
    )

    mock_scan = mocker.patch(
        "chatgpt2applenotes.exporters.apple_notes.AppleNotesExporter.scan_folder_notes",
        return_value={"conv-1": existing_note},
    )
    mock_export = mocker.patch(
        "chatgpt2applenotes.exporters.apple_notes.AppleNotesExporter.export",
    )

    from chatgpt2applenotes.sync import sync_conversations

    sync_conversations(tmp_path, "TestFolder")

    # export should be called with existing NoteInfo
    mock_export.assert_called_once()
    call_kwargs = mock_export.call_args.kwargs
    assert call_kwargs.get("existing") == existing_note
```

Step 2. Run test to verify it fails

Run: `uv run pytest tests/test_sync.py::test_sync_scans_folder_once -v`

Expected: FAIL (scan_folder_notes not called)

Step 3. Write minimal implementation

Modify `sync_conversations` in `chatgpt2applenotes/sync.py`:

```python
def sync_conversations(
    source: Path,
    folder: str,
    dry_run: bool = False,
    overwrite: bool = False,
    archive_deleted: bool = False,
    cc_dir: Optional[Path] = None,
) -> int:
    """
    syncs conversations from source to Apple Notes.

    Args:
        source: path to JSON file, directory, or ZIP archive
        folder: Apple Notes folder name
        dry_run: if True, don't write to Apple Notes
        overwrite: if True, replace notes instead of appending
        archive_deleted: if True, move orphaned notes to Archive
        cc_dir: optional directory to save copies of generated HTML

    Returns:
        exit code (0 success, 1 partial failure, 2 fatal error)
    """
    files = discover_files(source)
    if not files:
        logger.warning("No JSON files found in %s", source)
        return 0

    logger.info("Found %d conversation(s) to process", len(files))

    exporter = AppleNotesExporter(target="notes", cc_dir=cc_dir)

    # single upfront scan of destination folder
    note_index = exporter.scan_folder_notes(folder) if not dry_run else {}

    processed = 0
    failed = 0
    conversation_ids: list[str] = []

    for json_path in files:
        try:
            result = _process_file(
                json_path, exporter, folder, dry_run, overwrite, note_index
            )
            if result:
                conversation_ids.append(result)
                processed += 1
        except Exception as e:
            logger.error("Failed: %s - %s", json_path.name, e)
            failed += 1

    # handles archive-deleted if requested
    if archive_deleted and not dry_run:
        _archive_deleted_notes(exporter, folder, conversation_ids, note_index)

    # prints summary
    logger.info(
        "Processed %d conversation(s): %d synced, %d failed",
        processed + failed,
        processed,
        failed,
    )

    if failed > 0:
        return 1
    return 0
```

Update `_process_file`:

```python
def _process_file(
    json_path: Path,
    exporter: AppleNotesExporter,
    folder: str,
    dry_run: bool,
    overwrite: bool,
    note_index: dict,
) -> Optional[str]:
    """
    processes a single JSON file.

    Returns:
        conversation ID if successful, None otherwise
    """
    with open(json_path, encoding="utf-8") as f:
        json_data = json.load(f)

    conversation = process_conversation(json_data)
    logger.debug("Processing: %s", conversation.title)

    # looks up existing note from index
    existing = note_index.get(conversation.id)

    exporter.export(
        conversation=conversation,
        destination=folder,
        dry_run=dry_run,
        overwrite=overwrite,
        existing=existing,
    )

    return conversation.id
```

Update `_archive_deleted_notes`:

```python
def _archive_deleted_notes(
    exporter: AppleNotesExporter,
    folder: str,
    conversation_ids: list[str],
    note_index: dict,
) -> None:
    """moves notes not in conversation_ids to Archive subfolder."""
    source_ids = set(conversation_ids)

    archived = 0
    for conv_id, note_info in note_index.items():
        if conv_id not in source_ids:
            if exporter.move_note_to_archive_by_id(note_info.note_id, folder):
                logger.info("Archived: %s", conv_id)
                archived += 1

    if archived:
        logger.info("Archived %d note(s)", archived)
```

Step 4. Run tests to verify they pass

Run: `uv run pytest tests/test_sync.py -v`

Expected: All PASS

Step 5. Commit

```bash
git add chatgpt2applenotes/sync.py tests/test_sync.py
git commit -m "feat: use single-pass folder scan in sync_conversations"
```

---

## Task 11: Run Full Test Suite and Fix Any Issues

Step 1. Run all tests

Run: `uv run pytest -v`

Expected: All tests pass

Step 2. Run linters

Run: `uv run pre-commit run --all-files`

Expected: All pass

Step 3. Commit any fixes if needed

```bash
git add -A
git commit -m "fix: address linter/test issues"
```

---

## Task 12: Manual Integration Test

Step 1. Test with real Apple Notes folder

Run sync with a small set of conversations to verify:

1. Initial sync creates notes correctly
2. Re-sync detects existing notes and appends/updates
3. Archive operation moves orphaned notes

Step 2. Verify performance improvement

Time the sync before and after with 200+ conversations.

Step 3. Final commit if any adjustments needed

```bash
git add -A
git commit -m "fix: integration test adjustments"
```
