"""audio part handlers for multimodal content."""

import html
from typing import Any

from chatgpt2applenotes.exporters.handlers import RenderContext
from chatgpt2applenotes.exporters.handlers.parts import part_handler


@part_handler("audio_transcription")
class AudioTranscriptionHandler:  # pylint: disable=too-few-public-methods
    """renders audio transcription text."""

    def render(self, part: dict[str, Any], _ctx: RenderContext) -> str:
        """renders audio transcription as italicized quoted text."""
        text = part.get("text", "")
        escaped = html.escape(text)
        return f'<div><i>"{escaped}"</i></div>'


@part_handler("audio_asset_pointer", internal=True)
class AudioAssetHandler:  # pylint: disable=too-few-public-methods
    """renders audio asset pointer placeholder."""

    def render(self, _part: dict[str, Any], _ctx: RenderContext) -> str:
        """renders placeholder for audio attachment."""
        return "<div><i>[Audio attachment]</i></div>"


@part_handler("real_time_user_audio_video_asset_pointer", internal=True)
class RealTimeAudioVideoHandler:  # pylint: disable=too-few-public-methods
    """renders real-time audio/video pointer placeholder."""

    def render(self, _part: dict[str, Any], _ctx: RenderContext) -> str:
        """renders placeholder for voice/video input."""
        return "<div><i>[Voice/video input]</i></div>"
