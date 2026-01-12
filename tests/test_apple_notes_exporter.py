"""Tests for Apple Notes exporter."""

import json
import os
from pathlib import Path

import pytest

from chatgpt2applenotes.core.models import Author, Conversation, Message
from chatgpt2applenotes.core.parser import process_conversation
from chatgpt2applenotes.exporters.apple_notes import AppleNotesExporter

TEST_DATA_DIR = os.getenv(
    "CHATGPT_TEST_DATA_DIR",
    "/Users/acolomba/Downloads/chatgpt-export-json",
)


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


def test_metadata_includes_conversation_id_and_timestamp(tmp_path: Path) -> None:
    """Conversation metadata includes ID and timestamp."""
    conversation = Conversation(
        id="conv-abc123",
        title="Test",
        create_time=1234567890.0,
        update_time=1736629800.0,  # 2026-01-11 15:30 UTC
        messages=[
            Message(
                id="msg-1",
                author=Author(role="user"),
                create_time=1234567890.0,
                content={"content_type": "text", "parts": ["Hi"]},
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "conv-abc123" in html
    assert "Updated:" in html


def test_renders_messages_with_author_and_content(tmp_path: Path) -> None:
    """Messages show author role and content."""
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
                content={"content_type": "text", "parts": ["First message"]},
            ),
            Message(
                id="msg-2",
                author=Author(role="assistant"),
                create_time=1234567895.0,
                content={"content_type": "text", "parts": ["Second message"]},
            ),
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "<h2>User</h2>" in html
    assert "<h2>Assistant</h2>" in html
    assert "First message" in html
    assert "Second message" in html


def test_renders_markdown_in_messages(tmp_path: Path) -> None:
    """Markdown in message content is rendered to Apple Notes HTML."""
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
                content={
                    "content_type": "text",
                    "parts": ["**bold** and *italic* and `code`"],
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "<b>bold</b>" in html
    assert "<i>italic</i>" in html
    assert "<tt>code</tt>" in html


def test_renders_code_blocks(tmp_path: Path) -> None:
    """Code blocks are rendered with tt tags."""
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
                content={
                    "content_type": "text",
                    "parts": ["```python\nprint('hello')\n```"],
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "<div><tt>" in html
    assert "print('hello')" in html
    assert "</tt></div>" in html
    assert "<pre>" not in html
    assert '<code class="language' not in html


def test_renders_code_blocks_with_special_chars_in_language(tmp_path: Path) -> None:
    """Code blocks with special chars in language (c++, c#) render correctly."""
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
                content={
                    "content_type": "text",
                    "parts": ["```c++\nint main() {}\n```"],
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "<div><tt>" in html
    assert "int main() {}" in html
    assert "</tt></div>" in html
    assert "<pre>" not in html
    assert '<code class="language' not in html


def test_renders_lists(tmp_path: Path) -> None:
    """Lists are rendered as ul/ol with li items."""
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
                content={
                    "content_type": "text",
                    "parts": ["- Item 1\n- Item 2\n\n1. First\n2. Second"],
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "<ul>" in html
    assert "<li>Item 1</li>" in html
    assert "<li>Item 2</li>" in html
    assert "</ul>" in html
    assert "<ol>" in html
    assert "<li>First</li>" in html
    assert "<li>Second</li>" in html
    assert "</ol>" in html


def test_renders_multimodal_content_with_images(tmp_path: Path) -> None:
    """Multimodal content renders text and image parts."""
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
                content={
                    "content_type": "multimodal_text",
                    "parts": [
                        "Here is an image:",
                        {
                            "asset_pointer": "file-service://file-123",
                            "metadata": {
                                "dalle": {
                                    "prompt": "test image",
                                    "seed": 12345,
                                }
                            },
                            "size_bytes": 1000,
                            "width": 100,
                            "height": 100,
                        },
                    ],
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "Here is an image:" in html
    # for now, placeholder for image
    assert "[Image: file-service://file-123]" in html or "[Image" in html


@pytest.mark.skipif(
    not (Path(TEST_DATA_DIR) / "ChatGPT-Freezing_Rye_Bread.json").exists(),
    reason="Real conversation test file not available",
)
def test_export_real_conversation(tmp_path: Path) -> None:
    """Exports real ChatGPT conversation to Apple Notes HTML."""
    json_path = Path(TEST_DATA_DIR) / "ChatGPT-Freezing_Rye_Bread.json"

    with open(json_path, encoding="utf-8") as f:
        json_data = json.load(f)

    conversation = process_conversation(json_data)

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    # finds the generated HTML file
    html_files = list(output_dir.glob("*.html"))
    assert len(html_files) == 1, f"Expected 1 HTML file, found {len(html_files)}"
    output_file = html_files[0]
    assert output_file.exists()

    html = output_file.read_text(encoding="utf-8")
    assert "<html>" in html
    assert "<body>" in html
    assert conversation.title in html
    assert conversation.id in html
    # has messages
    assert len(conversation.messages) > 0
    assert "<h2>User</h2>" in html or "<h2>Assistant</h2>" in html
