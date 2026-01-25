"""tests for text content handler."""

from chatgpt2applenotes.exporters.handlers import RenderContext
from chatgpt2applenotes.exporters.handlers.text import TextHandler


def test_renders_simple_text() -> None:
    """renders simple text content."""
    handler = TextHandler()
    ctx = RenderContext()
    content = {"content_type": "text", "parts": ["Hello world"]}
    result = handler.render(content, None, ctx)
    assert "Hello world" in result


def test_renders_markdown() -> None:
    """renders markdown formatting."""
    handler = TextHandler()
    ctx = RenderContext()
    content = {"content_type": "text", "parts": ["**bold** and *italic*"]}
    result = handler.render(content, None, ctx)
    assert "<b>bold</b>" in result
    assert "<i>italic</i>" in result


def test_joins_multiple_parts() -> None:
    """joins multiple parts with newlines."""
    handler = TextHandler()
    ctx = RenderContext()
    content = {"content_type": "text", "parts": ["part 1", "part 2"]}
    result = handler.render(content, None, ctx)
    assert "part 1" in result
    assert "part 2" in result


def test_preserves_latex() -> None:
    """preserves LaTeX in text content."""
    handler = TextHandler()
    ctx = RenderContext()
    content = {"content_type": "text", "parts": ["Formula $a_1$ here"]}
    result = handler.render(content, None, ctx)
    assert "$a_1$" in result


def test_renders_citations() -> None:
    """renders citations from metadata."""
    handler = TextHandler()
    ctx = RenderContext()
    content = {"content_type": "text", "parts": ["See this. \ue200cite\ue202t0\ue201"]}
    metadata = {
        "content_references": [
            {
                "matched_text": "\ue200cite\ue202t0\ue201",
                "items": [{"url": "https://example.com", "attribution": "Example"}],
            }
        ]
    }
    result = handler.render(content, metadata, ctx)
    assert '<a href="https://example.com">Example</a>' in result


def test_removes_footnote_marks() -> None:
    """removes footnote marks like citation patterns."""
    handler = TextHandler()
    ctx = RenderContext()
    content = {
        "content_type": "text",
        "parts": ["Text\u301011\u2020(source)\u3011here"],
    }
    result = handler.render(content, None, ctx)
    # the \u3010...\u3011 pattern should be removed
    assert "\u3010" not in result


def test_handles_empty_parts() -> None:
    """handles empty or None parts gracefully."""
    handler = TextHandler()
    ctx = RenderContext()
    content = {"content_type": "text", "parts": None}
    result = handler.render(content, None, ctx)
    assert result is not None
