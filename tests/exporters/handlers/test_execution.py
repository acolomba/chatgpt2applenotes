"""tests for execution output content handler."""

from chatgpt2applenotes.exporters.handlers import RenderContext
from chatgpt2applenotes.exporters.handlers.execution import ExecutionOutputHandler


def test_renders_text_output_as_pre() -> None:
    """renders text output in pre block."""
    handler = ExecutionOutputHandler()
    ctx = RenderContext()
    content = {"content_type": "execution_output", "text": "Hello, World!"}
    result = handler.render(content, None, ctx)
    assert "<pre>" in result
    assert "Hello, World!" in result


def test_escapes_html_in_output() -> None:
    """escapes HTML in execution output."""
    handler = ExecutionOutputHandler()
    ctx = RenderContext()
    content = {"content_type": "execution_output", "text": "<script>alert(1)</script>"}
    result = handler.render(content, None, ctx)
    assert "<script>" not in result
    assert "&lt;script&gt;" in result


def test_renders_image_from_metadata() -> None:
    """renders image from aggregate_result.messages when present."""
    handler = ExecutionOutputHandler()
    ctx = RenderContext()
    content = {"content_type": "execution_output", "text": ""}
    metadata = {
        "aggregate_result": {
            "messages": [
                {"message_type": "image", "image_url": "data:image/png;base64,ABC123"}
            ]
        }
    }
    result = handler.render(content, metadata, ctx)
    assert "<img" in result
    assert "data:image/png;base64,ABC123" in result


def test_prefers_image_over_text() -> None:
    """prefers image output when both image and text are present."""
    handler = ExecutionOutputHandler()
    ctx = RenderContext()
    content = {"content_type": "execution_output", "text": "some text"}
    metadata = {
        "aggregate_result": {
            "messages": [
                {"message_type": "image", "image_url": "data:image/png;base64,XYZ"}
            ]
        }
    }
    result = handler.render(content, metadata, ctx)
    assert "<img" in result


def test_handles_missing_text() -> None:
    """handles missing text field gracefully."""
    handler = ExecutionOutputHandler()
    ctx = RenderContext()
    content = {"content_type": "execution_output"}
    result = handler.render(content, None, ctx)
    assert "<pre>" in result


def test_handles_empty_text() -> None:
    """handles empty text field."""
    handler = ExecutionOutputHandler()
    ctx = RenderContext()
    content = {"content_type": "execution_output", "text": ""}
    result = handler.render(content, None, ctx)
    assert "<pre>" in result


def test_renders_multiple_images() -> None:
    """renders all images from aggregate_result.messages."""
    handler = ExecutionOutputHandler()
    ctx = RenderContext()
    content = {"content_type": "execution_output", "text": ""}
    metadata = {
        "aggregate_result": {
            "messages": [
                {"message_type": "image", "image_url": "data:image/png;base64,IMG1"},
                {"message_type": "image", "image_url": "data:image/png;base64,IMG2"},
            ]
        }
    }
    result = handler.render(content, metadata, ctx)
    assert "IMG1" in result
    assert "IMG2" in result
    assert result.count("<img") == 2
