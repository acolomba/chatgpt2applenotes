"""tests for app pairing content handler."""

from chatgpt2applenotes.exporters.handlers import RenderContext
from chatgpt2applenotes.exporters.handlers.app_context import AppPairingContentHandler


def test_renders_workspace_info() -> None:
    """renders workspace app name and title."""
    handler = AppPairingContentHandler()
    ctx = RenderContext()
    content = {
        "content_type": "app_pairing_content",
        "workspaces": [{"app_name": "Terminal", "title": "bash"}],
    }
    result = handler.render(content, None, ctx)
    assert "Terminal" in result
    assert "bash" in result
    assert "<b>" in result


def test_renders_context_preview() -> None:
    """renders context parts preview."""
    handler = AppPairingContentHandler()
    ctx = RenderContext()
    content = {
        "content_type": "app_pairing_content",
        "workspaces": [],
        "context_parts": [{"text": "Some context text here"}],
    }
    result = handler.render(content, None, ctx)
    assert "Some context text" in result


def test_truncates_long_context() -> None:
    """truncates long context to 200 chars."""
    handler = AppPairingContentHandler()
    ctx = RenderContext()
    long_text = "x" * 300
    content = {
        "content_type": "app_pairing_content",
        "workspaces": [],
        "context_parts": [{"text": long_text}],
    }
    result = handler.render(content, None, ctx)
    assert "..." in result
    assert len(result) < len(long_text)


def test_escapes_html() -> None:
    """escapes HTML in content."""
    handler = AppPairingContentHandler()
    ctx = RenderContext()
    content = {
        "content_type": "app_pairing_content",
        "workspaces": [{"app_name": "<script>", "title": "test"}],
    }
    result = handler.render(content, None, ctx)
    assert "<script>" not in result
    assert "&lt;script&gt;" in result


def test_handles_empty_content() -> None:
    """handles empty workspaces and context."""
    handler = AppPairingContentHandler()
    ctx = RenderContext()
    content = {
        "content_type": "app_pairing_content",
        "workspaces": [],
        "context_parts": [],
    }
    result = handler.render(content, None, ctx)
    assert result == ""


def test_handles_app_name_only() -> None:
    """handles workspace with only app name."""
    handler = AppPairingContentHandler()
    ctx = RenderContext()
    content = {
        "content_type": "app_pairing_content",
        "workspaces": [{"app_name": "Safari"}],
    }
    result = handler.render(content, None, ctx)
    assert "Safari" in result
