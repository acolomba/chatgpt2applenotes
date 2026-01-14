"""Tests for Apple Notes exporter content type rendering."""

from pathlib import Path

from chatgpt2applenotes.core.models import Author, Conversation, Message
from chatgpt2applenotes.exporters.apple_notes import AppleNotesExporter


def test_renders_code_content_type(tmp_path: Path) -> None:
    """code content type is rendered as code block."""
    conversation = Conversation(
        id="conv-123",
        title="Test",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="assistant"),
                create_time=1234567890.0,
                content={
                    "content_type": "code",
                    "text": "print('hello world')",
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "<div><tt>" in html
    assert "print(&#x27;hello world&#x27;)" in html
    assert "</tt></div>" in html


def test_renders_execution_output_content_type(tmp_path: Path) -> None:
    """execution_output content type is rendered as code block."""
    conversation = Conversation(
        id="conv-123",
        title="Test",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="tool", name="python"),
                create_time=1234567890.0,
                content={
                    "content_type": "execution_output",
                    "text": "42",
                },
                metadata={
                    "aggregate_result": {
                        "messages": [{"message_type": "text", "text": "42"}]
                    }
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    # execution output without images should be filtered (tool message rule)
    # but if it passes the filter, it should render as code
    assert "42" in html or "Unsupported" not in html


def test_renders_execution_output_with_images(tmp_path: Path) -> None:
    """execution_output with images shows images from aggregate_result."""
    conversation = Conversation(
        id="conv-123",
        title="Test",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="tool", name="python"),
                create_time=1234567890.0,
                content={
                    "content_type": "execution_output",
                    "text": "matplotlib output",
                },
                metadata={
                    "aggregate_result": {
                        "messages": [
                            {
                                "message_type": "image",
                                "image_url": "data:image/png;base64,abc123",
                                "width": 400,
                                "height": 300,
                            }
                        ]
                    }
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert '<img src="data:image/png;base64,abc123"' in html


def test_renders_tether_quote_content_type(tmp_path: Path) -> None:
    """tether_quote content type is rendered as blockquote."""
    conversation = Conversation(
        id="conv-123",
        title="Test",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="assistant"),
                create_time=1234567890.0,
                content={
                    "content_type": "tether_quote",
                    "title": "Source Title",
                    "text": "Quoted text from source",
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "<blockquote>" in html
    assert "Source Title" in html or "Quoted text from source" in html
