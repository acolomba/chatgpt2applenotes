"""tests for HTML exporter."""

from pathlib import Path

from chatgpt2applenotes.core.models import Author, Conversation, Message
from chatgpt2applenotes.exporters.html import HTMLExporter


def test_html_exporter_basic(tmp_path: Path) -> None:
    """Test basic HTML export."""
    conversation = Conversation(
        id="conv-123",
        title="Test Conversation",
        create_time=1234567890.0,
        update_time=1234567890.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="user"),
                create_time=1234567890.0,
                content={"content_type": "text", "parts": ["Hello"]},
            )
        ],
    )

    exporter = HTMLExporter()
    output_dir = tmp_path / "test"

    exporter.export(conversation, str(output_dir), dry_run=False, overwrite=True)

    output_file = output_dir / "ChatGPT-Test_Conversation.html"
    assert output_file.exists()

    html = output_file.read_text()
    assert "<!DOCTYPE html>" in html
    assert "Test Conversation" in html
    assert "Hello" in html


def test_html_exporter_dry_run(tmp_path: Path) -> None:
    """Test dry run mode doesn't write files."""
    conversation = Conversation(
        id="conv-123",
        title="Test",
        create_time=1234567890.0,
        update_time=1234567890.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="user"),
                create_time=1234567890.0,
                content={"content_type": "text", "parts": ["Hello"]},
            )
        ],
    )

    exporter = HTMLExporter()
    output_dir = tmp_path / "test"

    # dry run should not create file
    exporter.export(conversation, str(output_dir), dry_run=True, overwrite=True)

    output_file = output_dir / "ChatGPT-Test.html"
    assert not output_file.exists()


def test_html_exporter_no_overwrite(tmp_path: Path) -> None:
    """Test that existing files are not overwritten when overwrite=False."""
    conversation = Conversation(
        id="conv-123",
        title="Test",
        create_time=1234567890.0,
        update_time=1234567890.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="user"),
                create_time=1234567890.0,
                content={"content_type": "text", "parts": ["Hello"]},
            )
        ],
    )

    exporter = HTMLExporter()
    output_dir = tmp_path / "test"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "ChatGPT-Test.html"

    # creates existing file with different content
    output_file.write_text("ORIGINAL CONTENT", encoding="utf-8")

    # export with overwrite=False should not change file
    exporter.export(conversation, str(output_dir), dry_run=False, overwrite=False)

    content = output_file.read_text(encoding="utf-8")
    assert content == "ORIGINAL CONTENT"
