"""Tests for data models."""

from chatgpt2applenotes.core.models import Author, Conversation, Message


def test_conversation_creation() -> None:
    """Test creating a Conversation instance."""
    conv = Conversation(
        id="conv-123",
        title="Test Conversation",
        create_time=1234567890.0,
        update_time=1234567890.0,
        messages=[],
    )
    assert conv.id == "conv-123"
    assert conv.title == "Test Conversation"
    assert len(conv.messages) == 0


def test_message_creation() -> None:
    """Test creating a Message instance."""
    msg = Message(
        id="msg-123",
        author=Author(role="user", name=None, metadata={}),
        create_time=1234567890.0,
        content={"content_type": "text", "parts": ["Hello"]},
        metadata={},
    )
    assert msg.id == "msg-123"
    assert msg.author.role == "user"
    assert msg.content["parts"][0] == "Hello"
