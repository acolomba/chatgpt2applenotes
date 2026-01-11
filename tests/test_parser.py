"""Tests for conversation parser module."""

from chatgpt2applenotes.core.parser import process_conversation


def test_process_conversation_basic() -> None:
    """Test basic conversation processing with minimal JSON."""
    json_data = {
        "id": "conv-123",
        "title": "Test",
        "create_time": 1234567890.0,
        "update_time": 1234567890.0,
        "mapping": {
            "msg-1": {
                "id": "msg-1",
                "message": {
                    "id": "msg-1",
                    "author": {"role": "user"},
                    "create_time": 1234567890.0,
                    "content": {"content_type": "text", "parts": ["Hello"]},
                },
            }
        },
    }

    conversation = process_conversation(json_data)

    assert conversation.id == "conv-123"
    assert conversation.title == "Test"
    assert len(conversation.messages) == 1
    assert conversation.messages[0].content["parts"][0] == "Hello"
