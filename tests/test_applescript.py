"""tests for AppleScript module."""

from chatgpt2applenotes.exporters.applescript import NoteInfo


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
