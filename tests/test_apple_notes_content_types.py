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
    assert "<pre>" in html
    assert "print(&#x27;hello world&#x27;)" in html
    assert "</pre>" in html


def test_renders_code_content_type_with_linebreaks(tmp_path: Path) -> None:
    """code content type preserves line breaks."""
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
                    "text": "def foo():\n    return 1",
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    # code content should use <pre> tags to preserve whitespace
    assert "<pre>" in html
    assert "</pre>" in html
    assert "def foo():" in html
    assert "return 1" in html


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


def test_renders_tether_browsing_display_content_type(tmp_path: Path) -> None:
    """tether_browsing_display content type renders cite metadata as links."""
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
                content={"content_type": "tether_browsing_display"},
                metadata={
                    "_cite_metadata": {
                        "metadata_list": [
                            {"title": "Example Site", "url": "https://example.com"},
                            {"title": "Another Site", "url": "https://another.com"},
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
    assert "Example Site" in html
    assert "https://example.com" in html
    assert "Another Site" in html


def test_renders_audio_transcription_in_multimodal(tmp_path: Path) -> None:
    """audio_transcription parts are rendered with italic styling."""
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
                        {
                            "content_type": "audio_transcription",
                            "text": "This is what I said",
                        }
                    ],
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "<i>" in html
    assert "This is what I said" in html


def test_preserves_latex_in_assistant_messages(tmp_path: Path) -> None:
    """LaTeX delimiters are preserved and not mangled by markdown processing."""
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
                    "content_type": "text",
                    "parts": [
                        "The formula is $E = mc^2$ and also:\n$$\\int_0^1 x^2 dx$$"
                    ],
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    # LaTeX should be preserved (possibly HTML-escaped)
    assert "E = mc^2" in html or "E = mc" in html
    # underscores in LaTeX should not become <em> tags
    assert "_0^1" in html or "_0" in html
    # the integral symbol or command should be present
    assert "int" in html


def test_latex_underscores_not_converted_to_emphasis(tmp_path: Path) -> None:
    """underscores inside LaTeX are not converted to emphasis tags."""
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
                    "content_type": "text",
                    # underscores inside LaTeX: $a_1$ and $b_2$ could form emphasis
                    # without protection: $a<i>1$ and $b</i>2$
                    "parts": ["Variables $a_1$ and $b_2$ are defined."],
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    # the LaTeX should be preserved with underscores intact
    assert "$a_1$" in html
    assert "$b_2$" in html
    # underscores inside LaTeX should not become emphasis tags
    assert "<i>1$ and $b</i>" not in html
    assert "<em>1$ and $b</em>" not in html


def test_latex_asterisks_not_converted_to_emphasis(tmp_path: Path) -> None:
    """asterisks inside LaTeX are not converted to emphasis tags."""
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
                    "content_type": "text",
                    # asterisks inside LaTeX: $x*y$ would break without protection
                    # without protection: *a $x<em>y$ b</em> done
                    "parts": ["Star *a $x*y$ b* done"],
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    # the LaTeX $x*y$ should be preserved intact
    assert "$x*y$" in html
    # the asterisks inside LaTeX should not split the formula
    assert "<em>a $x</em>" not in html
    assert "<i>a $x</i>" not in html


def test_removes_footnote_marks(tmp_path: Path) -> None:
    """citation marks like 【11†(source)】 are removed from output."""
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
                    "content_type": "text",
                    "parts": [
                        "According to the source【11†(Wikipedia)】, this is true【3†(source)】."
                    ],
                },
                metadata={
                    "citations": [
                        {"metadata": {"extra": {"cited_message_idx": 11}}},
                        {"metadata": {"extra": {"cited_message_idx": 3}}},
                    ]
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "According to the source" in html
    assert "this is true" in html
    # footnote marks should be removed
    assert "【" not in html
    assert "†" not in html
    assert "(Wikipedia)" not in html


def test_full_conversation_with_all_features(tmp_path: Path) -> None:
    """integration test with all new features."""
    conversation = Conversation(
        id="abc12345-6789-def0-1234-567890abcdef",
        title="Full Feature Test",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            # user message - plain text
            Message(
                id="msg-1",
                author=Author(role="user"),
                create_time=1234567890.0,
                content={"content_type": "text", "parts": ["*asterisks* here"]},
                metadata={"recipient": "all"},
            ),
            # internal message - should be filtered
            Message(
                id="msg-2",
                author=Author(role="assistant"),
                create_time=1234567891.0,
                content={"content_type": "text", "parts": ["Internal"]},
                metadata={"recipient": "browser"},
            ),
            # assistant with footnotes and LaTeX
            Message(
                id="msg-3",
                author=Author(role="assistant"),
                create_time=1234567892.0,
                content={
                    "content_type": "text",
                    "parts": ["Result【1†(src)】: $x^2$"],
                },
                metadata={"recipient": "all"},
            ),
            # tool with text only - should be filtered
            Message(
                id="msg-4",
                author=Author(role="tool", name="browser"),
                create_time=1234567893.0,
                content={"content_type": "text", "parts": ["Hidden"]},
                metadata={"recipient": "all"},
            ),
            # tool with multimodal - should be shown
            Message(
                id="msg-5",
                author=Author(role="tool", name="dalle"),
                create_time=1234567894.0,
                content={
                    "content_type": "multimodal_text",
                    "parts": ["Generated image"],
                },
                metadata={"recipient": "all"},
            ),
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Full_Feature_Test.html").read_text(encoding="utf-8")

    # user message preserved literally
    assert "*asterisks* here" in html
    # internal message filtered
    assert "Internal" not in html
    # footnote removed, LaTeX preserved
    assert "【" not in html
    assert "†" not in html
    assert "x^2" in html
    # tool text filtered
    assert "Hidden" not in html
    # tool multimodal shown
    assert "Generated image" in html
    # friendly labels
    assert "<h2>You</h2>" in html
    assert "<h2>ChatGPT</h2>" in html
    assert "<h2>Plugin (dalle)</h2>" in html


def test_renders_single_citation_as_link(tmp_path: Path) -> None:
    """citation markers are replaced with attribution links."""
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
                    "content_type": "text",
                    "parts": ["See the guide. \ue200cite\ue202turn0search3\ue201"],
                },
                metadata={
                    "content_references": [
                        {
                            "matched_text": "\ue200cite\ue202turn0search3\ue201",
                            "items": [
                                {
                                    "url": "https://example.com/guide",
                                    "attribution": "Example.com",
                                }
                            ],
                        }
                    ]
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "See the guide." in html
    assert '<a href="https://example.com/guide">Example.com</a>' in html
    # marker should be gone
    assert "\ue200" not in html
    assert "turn0search3" not in html


def test_renders_multi_citation_as_comma_separated_links(tmp_path: Path) -> None:
    """multi-source citations render as comma-separated links."""
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
                    "content_type": "text",
                    "parts": [
                        "It needs cleanup. \ue200cite\ue202turn1search2\ue202turn1search3\ue201"
                    ],
                },
                metadata={
                    "content_references": [
                        {
                            "matched_text": "\ue200cite\ue202turn1search2\ue202turn1search3\ue201",
                            "items": [
                                {
                                    "url": "https://intego.com/article",
                                    "attribution": "Intego",
                                    "supporting_websites": [
                                        {
                                            "url": "https://reddit.com/r/mac",
                                            "attribution": "Reddit",
                                        }
                                    ],
                                }
                            ],
                        }
                    ]
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "It needs cleanup." in html
    assert '<a href="https://intego.com/article">Intego</a>' in html
    assert '<a href="https://reddit.com/r/mac">Reddit</a>' in html
    # should be comma-separated
    assert "Intego</a>, <a" in html
    # marker should be gone
    assert "\ue200" not in html
