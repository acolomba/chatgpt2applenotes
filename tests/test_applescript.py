"""tests for AppleScript module."""

import subprocess
from unittest.mock import MagicMock, patch

from chatgpt2applenotes.exporters.applescript import (
    NoteInfo,
    list_note_ids,
    read_note_body_by_id,
)


def test_noteinfo_creation() -> None:
    """tests NoteInfo dataclass holds note metadata."""
    info = NoteInfo(
        note_id="x-coredata://123",
        conversation_id="conv-uuid-1",
        last_message_id="msg-uuid-a",
    )
    assert info.note_id == "x-coredata://123"
    assert info.conversation_id == "conv-uuid-1"
    assert info.last_message_id == "msg-uuid-a"


def test_list_note_ids_returns_ids() -> None:
    """tests list_note_ids parses AppleScript output."""
    mock_result = MagicMock()
    mock_result.stdout = "x-coredata://id1\nx-coredata://id2\nx-coredata://id3\n"

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        result = list_note_ids("TestFolder")

    assert result == ["x-coredata://id1", "x-coredata://id2", "x-coredata://id3"]
    mock_run.assert_called_once()


def test_list_note_ids_returns_empty_on_error() -> None:
    """tests list_note_ids returns empty list on AppleScript error."""
    with patch(
        "subprocess.run", side_effect=subprocess.CalledProcessError(1, "osascript")
    ):
        result = list_note_ids("TestFolder")

    assert result == []


def test_list_note_ids_returns_empty_for_empty_folder() -> None:
    """tests list_note_ids returns empty list for empty folder."""
    mock_result = MagicMock()
    mock_result.stdout = ""

    with patch("subprocess.run", return_value=mock_result):
        result = list_note_ids("TestFolder")

    assert result == []


def test_read_note_body_by_id_returns_body() -> None:
    """tests read_note_body_by_id returns note body."""
    mock_result = MagicMock()
    mock_result.stdout = "<html><body>Note content</body></html>"

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        result = read_note_body_by_id("x-coredata://123")

    assert result == "<html><body>Note content</body></html>"
    mock_run.assert_called_once()


def test_read_note_body_by_id_returns_none_on_error() -> None:
    """tests read_note_body_by_id returns None on error."""
    with patch(
        "subprocess.run", side_effect=subprocess.CalledProcessError(1, "osascript")
    ):
        result = read_note_body_by_id("x-coredata://123")

    assert result is None


def test_read_note_body_by_id_returns_none_for_empty() -> None:
    """tests read_note_body_by_id returns None for empty body."""
    mock_result = MagicMock()
    mock_result.stdout = ""

    with patch("subprocess.run", return_value=mock_result):
        result = read_note_body_by_id("x-coredata://123")

    assert result is None
