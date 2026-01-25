"""tests for code content handler."""

from chatgpt2applenotes.exporters.handlers import RenderContext
from chatgpt2applenotes.exporters.handlers.code import CodeHandler


def test_renders_code_as_pre() -> None:
    """renders code content in pre block."""
    handler = CodeHandler()
    ctx = RenderContext()
    content = {
        "content_type": "code",
        "language": "python",
        "text": "print(42)",
    }
    result = handler.render(content, None, ctx)
    assert "<pre>" in result
    assert "</pre>" in result
    assert "print(42)" in result


def test_escapes_html_in_code() -> None:
    """escapes HTML tags in code content."""
    handler = CodeHandler()
    ctx = RenderContext()
    content = {
        "content_type": "code",
        "language": "html",
        "text": "<div>test</div>",
    }
    result = handler.render(content, None, ctx)
    assert "<div>test</div>" not in result
    assert "&lt;div&gt;" in result


def test_handles_missing_text() -> None:
    """handles missing text field gracefully."""
    handler = CodeHandler()
    ctx = RenderContext()
    content = {"content_type": "code", "language": "python"}
    result = handler.render(content, None, ctx)
    assert "<pre>" in result
    assert "</pre>" in result


def test_handles_empty_text() -> None:
    """handles empty text field."""
    handler = CodeHandler()
    ctx = RenderContext()
    content = {"content_type": "code", "language": "python", "text": ""}
    result = handler.render(content, None, ctx)
    assert "<pre>" in result


def test_multiline_code() -> None:
    """renders multiline code correctly."""
    handler = CodeHandler()
    ctx = RenderContext()
    content = {
        "content_type": "code",
        "language": "python",
        "text": "def foo():\n    return 42",
    }
    result = handler.render(content, None, ctx)
    assert "def foo():" in result
    assert "return 42" in result
