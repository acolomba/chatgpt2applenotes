"""tests for multimodal part registry."""

from typing import Any

from chatgpt2applenotes.exporters.handlers import RenderContext
from chatgpt2applenotes.exporters.handlers.parts import PartRegistry, part_handler


def test_part_handler_decorator_registers() -> None:
    """@part_handler decorator registers part handler."""
    registry = PartRegistry()

    @part_handler("test_part", target_registry=registry)
    class TestPartHandler:  # pylint: disable=unused-variable,too-few-public-methods
        """test handler for registration."""

        def render(self, _part: dict[str, Any], _ctx: RenderContext) -> str:
            """renders test part."""
            return "<span>test</span>"

    assert "test_part" in registry._handlers  # pylint: disable=protected-access


def test_part_registry_dispatches() -> None:
    """PartRegistry.render dispatches to correct handler."""
    registry = PartRegistry()

    @part_handler("audio_transcription", target_registry=registry)
    class AudioHandler:  # pylint: disable=unused-variable,too-few-public-methods
        """handler for audio transcription."""

        def render(self, part: dict[str, Any], _ctx: RenderContext) -> str:
            """renders audio transcription."""
            return f"<i>{part.get('text')}</i>"

    ctx = RenderContext()
    result = registry.render(
        {"content_type": "audio_transcription", "text": "hello"}, ctx
    )
    assert result == "<i>hello</i>"


def test_part_registry_returns_none_for_unknown() -> None:
    """PartRegistry.render returns None for unknown part type."""
    registry = PartRegistry()
    ctx = RenderContext()
    result = registry.render({"content_type": "unknown_part"}, ctx)
    assert result is None


def test_internal_part_skipped_without_flag() -> None:
    """internal part handler skipped when render_internals=False."""
    registry = PartRegistry()

    @part_handler("audio_asset_pointer", internal=True, target_registry=registry)
    class AudioAssetHandler:  # pylint: disable=unused-variable,too-few-public-methods
        """handler for audio asset pointer."""

        def render(self, _part: dict[str, Any], _ctx: RenderContext) -> str:
            """renders audio asset pointer."""
            return "[audio]"

    ctx = RenderContext(render_internals=False)
    result = registry.render({"content_type": "audio_asset_pointer"}, ctx)
    assert result is None


def test_internal_part_rendered_with_flag() -> None:
    """internal part handler renders when render_internals=True."""
    registry = PartRegistry()

    @part_handler("audio_asset_pointer", internal=True, target_registry=registry)
    class AudioAssetHandler:  # pylint: disable=unused-variable,too-few-public-methods
        """handler for audio asset pointer."""

        def render(self, _part: dict[str, Any], _ctx: RenderContext) -> str:
            """renders audio asset pointer."""
            return "[audio]"

    ctx = RenderContext(render_internals=True)
    result = registry.render({"content_type": "audio_asset_pointer"}, ctx)
    assert result == "[audio]"
