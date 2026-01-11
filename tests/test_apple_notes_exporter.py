"""Tests for Apple Notes exporter."""

from pathlib import Path

from chatgpt2applenotes.core.models import Author, Conversation, Message
from chatgpt2applenotes.exporters.apple_notes import AppleNotesExporter


def test_export_to_file_creates_html(tmp_path: Path) -> None:
    """Exporter creates HTML file for conversation."""
    conversation = Conversation(
        id="conv-123",
        title="Test Conversation",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="user"),
                create_time=1234567890.0,
                content={"content_type": "text", "parts": ["Hello"]},
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"

    exporter.export(conversation, str(output_dir))

    output_file = output_dir / "Test_Conversation.html"
    assert output_file.exists()

    html = output_file.read_text(encoding="utf-8")
    assert "<html>" in html
    assert "<body>" in html
    assert "Test Conversation" in html
    assert "Hello" in html


def test_export_handles_empty_title(tmp_path: Path) -> None:
    """Uses conversation ID as filename when title is empty or invalid."""
    conversation = Conversation(
        id="conv-fallback-123",
        title="///",  # only special chars
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="user"),
                create_time=1234567890.0,
                content={"content_type": "text", "parts": ["Test"]},
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    output_file = output_dir / "conv-fallback-123.html"
    assert output_file.exists()


def test_export_respects_overwrite_false(tmp_path: Path) -> None:
    """Does not overwrite existing file when overwrite=False."""
    conversation = Conversation(
        id="conv-123",
        title="Test",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="user"),
                create_time=1234567890.0,
                content={"content_type": "text", "parts": ["Original"]},
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    output_dir.mkdir(parents=True)
    output_file = output_dir / "Test.html"

    # create existing file
    output_file.write_text("EXISTING CONTENT", encoding="utf-8")

    # export with overwrite=False should not change file
    exporter.export(conversation, str(output_dir), overwrite=False)

    content = output_file.read_text(encoding="utf-8")
    assert content == "EXISTING CONTENT"


def test_export_escapes_html_in_content(tmp_path: Path) -> None:
    """HTML special characters are escaped to prevent injection."""
    conversation = Conversation(
        id="conv-123",
        title="<script>alert('XSS')</script>",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="user"),
                create_time=1234567890.0,
                content={
                    "content_type": "text",
                    "parts": ["<b>test</b> & <i>more</i>"],
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html_file = list(output_dir.glob("*.html"))[0]
    html = html_file.read_text(encoding="utf-8")

    # title should be escaped
    assert "&lt;script&gt;" in html
    assert "alert('XSS')" not in html or "<script>alert('XSS')</script>" not in html

    # message content should be escaped
    assert "&lt;b&gt;test&lt;/b&gt; &amp; &lt;i&gt;more&lt;/i&gt;" in html
