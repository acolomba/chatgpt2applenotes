"""tests for AppleScript module."""

import subprocess
from unittest.mock import MagicMock, patch

from chatgpt2applenotes.exporters.applescript import (
    NoteInfo,
    list_note_ids,
    read_note_body_by_id,
    scan_folder_notes,
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


def test_scan_folder_notes_builds_index() -> None:
    """tests scan_folder_notes builds conversation_id -> NoteInfo index."""
    # uses proper UUID format for matching regex
    body1 = (
        '<html>Content 1<p style="color:gray">'
        "a1b2c3d4-e5f6-7890-abcd-ef1234567890:11111111-2222-3333-4444-555555555555"
        "</p></html>"
    )
    body2 = (
        '<html>Content 2<p style="color:gray">'
        "b2c3d4e5-f6a7-8901-bcde-f12345678901:22222222-3333-4444-5555-666666666666"
        "</p></html>"
    )

    with (
        patch(
            "chatgpt2applenotes.exporters.applescript.list_note_ids",
            return_value=["x-coredata://id1", "x-coredata://id2"],
        ),
        patch(
            "chatgpt2applenotes.exporters.applescript.read_note_body_by_id",
            side_effect=[body1, body2],
        ),
    ):
        result = scan_folder_notes("TestFolder")

    assert len(result) == 2
    assert "a1b2c3d4-e5f6-7890-abcd-ef1234567890" in result
    assert "b2c3d4e5-f6a7-8901-bcde-f12345678901" in result
    assert result["a1b2c3d4-e5f6-7890-abcd-ef1234567890"].note_id == "x-coredata://id1"
    assert (
        result["a1b2c3d4-e5f6-7890-abcd-ef1234567890"].last_message_id
        == "11111111-2222-3333-4444-555555555555"
    )
    assert result["b2c3d4e5-f6a7-8901-bcde-f12345678901"].note_id == "x-coredata://id2"
    assert (
        result["b2c3d4e5-f6a7-8901-bcde-f12345678901"].last_message_id
        == "22222222-3333-4444-5555-666666666666"
    )


def test_scan_folder_notes_skips_notes_without_footer() -> None:
    """tests scan_folder_notes skips notes without valid footer."""
    body1 = "<html>Content without footer</html>"
    body2 = (
        '<html>Content 2<p style="color:gray">'
        "b2c3d4e5-f6a7-8901-bcde-f12345678901:22222222-3333-4444-5555-666666666666"
        "</p></html>"
    )

    with (
        patch(
            "chatgpt2applenotes.exporters.applescript.list_note_ids",
            return_value=["x-coredata://id1", "x-coredata://id2"],
        ),
        patch(
            "chatgpt2applenotes.exporters.applescript.read_note_body_by_id",
            side_effect=[body1, body2],
        ),
    ):
        result = scan_folder_notes("TestFolder")

    assert len(result) == 1
    assert "b2c3d4e5-f6a7-8901-bcde-f12345678901" in result


def test_scan_folder_notes_returns_empty_for_empty_folder() -> None:
    """tests scan_folder_notes returns empty dict for empty folder."""
    with patch(
        "chatgpt2applenotes.exporters.applescript.list_note_ids",
        return_value=[],
    ):
        result = scan_folder_notes("TestFolder")

    assert not result
