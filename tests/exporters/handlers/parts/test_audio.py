"""tests for audio part handlers."""

# pylint: disable=redefined-outer-name

import pytest

from chatgpt2applenotes.exporters.handlers import RenderContext
from chatgpt2applenotes.exporters.handlers.parts.audio import (
    AudioAssetHandler,
    AudioTranscriptionHandler,
    RealTimeAudioVideoHandler,
)


@pytest.fixture
def ctx() -> RenderContext:
    """provides render context without internals."""
    return RenderContext()


@pytest.fixture
def ctx_internals() -> RenderContext:
    """provides render context with internals enabled."""
    return RenderContext(render_internals=True)


class TestAudioTranscriptionHandler:
    """tests for AudioTranscriptionHandler."""

    def test_renders_transcription(self, ctx: RenderContext) -> None:
        """renders audio transcription as italicized quoted text."""
        handler = AudioTranscriptionHandler()
        part = {"content_type": "audio_transcription", "text": "Hello world"}
        result = handler.render(part, ctx)
        assert "<i>" in result
        assert "Hello world" in result
        assert '"' in result  # quoted

    def test_escapes_html(self, ctx: RenderContext) -> None:
        """escapes HTML in transcription text."""
        handler = AudioTranscriptionHandler()
        part = {"content_type": "audio_transcription", "text": "<script>bad</script>"}
        result = handler.render(part, ctx)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


class TestAudioAssetHandler:
    """tests for AudioAssetHandler."""

    def test_renders_placeholder(self, ctx_internals: RenderContext) -> None:
        """renders audio asset as placeholder."""
        handler = AudioAssetHandler()
        part = {
            "content_type": "audio_asset_pointer",
            "asset_pointer": "sediment://...",
        }
        result = handler.render(part, ctx_internals)
        assert "[Audio" in result or "audio" in result.lower()

    def test_is_internal(self) -> None:
        """audio asset handler is marked as internal."""
        # pylint: disable=no-member
        assert AudioAssetHandler.internal is True  # type: ignore[attr-defined]


class TestRealTimeAudioVideoHandler:
    """tests for RealTimeAudioVideoHandler."""

    def test_renders_placeholder(self, ctx_internals: RenderContext) -> None:
        """renders real-time audio/video as placeholder."""
        handler = RealTimeAudioVideoHandler()
        part = {"content_type": "real_time_user_audio_video_asset_pointer"}
        result = handler.render(part, ctx_internals)
        assert "[" in result  # placeholder indicator

    def test_is_internal(self) -> None:
        """real-time handler is marked as internal."""
        # pylint: disable=no-member
        assert RealTimeAudioVideoHandler.internal is True  # type: ignore[attr-defined]
