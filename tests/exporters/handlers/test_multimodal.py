"""tests for multimodal text content handler."""

# pylint: disable=redefined-outer-name,unused-import,wrong-import-order

import pytest

# imports audio handlers to register them in the global part registry
import chatgpt2applenotes.exporters.handlers.parts.audio  # noqa: F401
from chatgpt2applenotes.exporters.handlers import RenderContext
from chatgpt2applenotes.exporters.handlers.multimodal import MultimodalHandler


@pytest.fixture
def handler() -> MultimodalHandler:
    """provides multimodal handler instance."""
    return MultimodalHandler()


@pytest.fixture
def ctx() -> RenderContext:
    """provides render context without internals."""
    return RenderContext()


@pytest.fixture
def ctx_internals() -> RenderContext:
    """provides render context with internals enabled."""
    return RenderContext(render_internals=True)


class TestMultimodalHandler:
    """tests for MultimodalHandler."""

    def test_renders_string_parts_as_markdown(
        self, handler: MultimodalHandler, ctx: RenderContext
    ) -> None:
        """renders string parts as markdown."""
        content = {"content_type": "multimodal_text", "parts": ["Hello **world**"]}
        result = handler.render(content, None, ctx)
        assert "<b>world</b>" in result

    def test_renders_audio_transcription_part(
        self, handler: MultimodalHandler, ctx: RenderContext
    ) -> None:
        """renders audio_transcription parts."""
        content = {
            "content_type": "multimodal_text",
            "parts": [{"content_type": "audio_transcription", "text": "Hello there"}],
        }
        result = handler.render(content, None, ctx)
        assert "Hello there" in result

    def test_renders_mixed_parts(
        self, handler: MultimodalHandler, ctx: RenderContext
    ) -> None:
        """renders mixed string and object parts."""
        content = {
            "content_type": "multimodal_text",
            "parts": [
                "Some **text**",
                {"content_type": "audio_transcription", "text": "Voice input"},
            ],
        }
        result = handler.render(content, None, ctx)
        assert "<b>text</b>" in result
        assert "Voice input" in result

    def test_skips_unknown_parts(
        self, handler: MultimodalHandler, ctx: RenderContext
    ) -> None:
        """skips unknown part types gracefully."""
        content = {
            "content_type": "multimodal_text",
            "parts": [
                "Text",
                {"content_type": "unknown_type", "data": "something"},
            ],
        }
        result = handler.render(content, None, ctx)
        assert "Text" in result
        # unknown type should not cause error

    def test_skips_internal_parts_without_flag(
        self, handler: MultimodalHandler, ctx: RenderContext
    ) -> None:
        """skips internal parts when render_internals=False."""
        content = {
            "content_type": "multimodal_text",
            "parts": [
                {
                    "content_type": "audio_asset_pointer",
                    "asset_pointer": "sediment://...",
                }
            ],
        }
        result = handler.render(content, None, ctx)
        # audio_asset_pointer is internal, should be skipped
        assert result == "" or "Audio" not in result

    def test_renders_internal_parts_with_flag(
        self, handler: MultimodalHandler, ctx_internals: RenderContext
    ) -> None:
        """renders internal parts when render_internals=True."""
        content = {
            "content_type": "multimodal_text",
            "parts": [
                {
                    "content_type": "audio_asset_pointer",
                    "asset_pointer": "sediment://...",
                }
            ],
        }
        result = handler.render(content, None, ctx_internals)
        # audio_asset_pointer is internal, should render with flag
        assert "Audio" in result

    def test_handles_empty_parts(
        self, handler: MultimodalHandler, ctx: RenderContext
    ) -> None:
        """handles empty parts list."""
        content = {"content_type": "multimodal_text", "parts": []}
        result = handler.render(content, None, ctx)
        assert result == ""

    def test_handles_none_parts(
        self, handler: MultimodalHandler, ctx: RenderContext
    ) -> None:
        """handles None parts gracefully."""
        content = {"content_type": "multimodal_text", "parts": None}
        result = handler.render(content, None, ctx)
        assert result == ""
