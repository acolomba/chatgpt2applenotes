"""tests for system error content handler."""

from chatgpt2applenotes.exporters.handlers import RenderContext
from chatgpt2applenotes.exporters.handlers.errors import SystemErrorHandler


def test_renders_error_with_name() -> None:
    """renders error with name indicator."""
    handler = SystemErrorHandler()
    ctx = RenderContext()
    content = {
        "content_type": "system_error",
        "name": "ChatGPTAgentToolException",
        "text": "Something went wrong",
    }
    result = handler.render(content, None, ctx)
    assert "ChatGPTAgentToolException" in result
    # should have some warning indicator
    assert (
        "\u26a0" in result or "warning" in result.lower() or "error" in result.lower()
    )


def test_escapes_html_in_text() -> None:
    """escapes HTML in error text."""
    handler = SystemErrorHandler()
    ctx = RenderContext()
    content = {
        "content_type": "system_error",
        "name": "Error",
        "text": "<script>bad</script>",
    }
    result = handler.render(content, None, ctx)
    assert "<script>" not in result
    assert "&lt;script&gt;" in result


def test_handles_missing_text() -> None:
    """handles missing text field gracefully."""
    handler = SystemErrorHandler()
    ctx = RenderContext()
    content = {"content_type": "system_error", "name": "Error"}
    result = handler.render(content, None, ctx)
    assert "Error" in result


def test_handles_missing_name() -> None:
    """handles missing name field gracefully."""
    handler = SystemErrorHandler()
    ctx = RenderContext()
    content = {"content_type": "system_error", "text": "Something failed"}
    result = handler.render(content, None, ctx)
    # should still render something
    assert result is not None
    assert len(result) > 0
