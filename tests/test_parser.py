"""Tests for conversation parser module."""

import json
from pathlib import Path

import pytest

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


@pytest.mark.skipif(
    not Path(
        "/Users/acolomba/Downloads/chatgpt-export-json/ChatGPT-Freezing_Rye_Bread.json"
    ).exists(),
    reason="Real conversation test file not available",
)
def test_process_real_conversation() -> None:
    """Test with actual ChatGPT export file."""
    json_path = Path(
        "/Users/acolomba/Downloads/chatgpt-export-json/ChatGPT-Freezing_Rye_Bread.json"
    )

    with open(json_path, encoding="utf-8") as f:
        json_data = json.load(f)

    conversation = process_conversation(json_data)

    # Basic validations
    assert conversation.id
    assert conversation.title == "Freezing Rye Bread"
    assert len(conversation.messages) > 0

    # Verify message structure
    for msg in conversation.messages:
        assert msg.id
        assert msg.author.role in ["user", "assistant", "system"]
        assert msg.create_time > 0


def test_skip_messages_without_timestamp() -> None:
    """Messages without create_time should be filtered out."""
    json_data = {
        "id": "conv-123",
        "title": "Test",
        "create_time": 1234567890.0,
        "update_time": 1234567890.0,
        "mapping": {
            "msg-1": {
                "message": {
                    "id": "msg-1",
                    "author": {"role": "user"},
                    "create_time": 1234567890.0,
                    "content": {"content_type": "text", "parts": ["Valid"]},
                }
            },
            "msg-2": {
                "message": {
                    "id": "msg-2",
                    "author": {"role": "user"},
                    # Missing create_time
                    "content": {"content_type": "text", "parts": ["Invalid"]},
                }
            },
        },
    }

    conversation = process_conversation(json_data)
    assert len(conversation.messages) == 1
    assert conversation.messages[0].content["parts"][0] == "Valid"
