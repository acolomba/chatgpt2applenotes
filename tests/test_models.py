"""Tests for data models."""

from chatgpt2applenotes.core.models import (
    Author,
    Conversation,
    Message,
    MessageContent,
)


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


def test_metadata_isolation() -> None:
    """Verify metadata dicts are not shared between instances."""
    a1 = Author(role="user")
    a2 = Author(role="assistant")
    # After __post_init__, metadata is guaranteed to be a dict
    assert a1.metadata is not None
    assert a2.metadata is not None
    a1.metadata["key"] = "value1"
    assert "key" not in a2.metadata


def test_metadata_defaults_to_empty_dict() -> None:
    """Verify None metadata becomes empty dict."""
    author = Author(role="user", metadata=None)
    assert author.metadata == {}
    assert isinstance(author.metadata, dict)


def test_explicit_metadata_preserved() -> None:
    """Verify explicit metadata dict is used."""
    custom_meta = {"custom": "data"}
    author = Author(role="user", metadata=custom_meta)
    assert author.metadata == custom_meta


def test_author_with_name() -> None:
    """Test Author with optional name field."""
    author = Author(role="assistant", name="GPT-4")
    assert author.name == "GPT-4"


def test_message_content_creation() -> None:
    """Test MessageContent dataclass."""
    content = MessageContent(content_type="text", parts=["Hello", "World"])
    assert content.content_type == "text"
    assert len(content.parts) == 2
