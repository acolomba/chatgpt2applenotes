"""tests for handler registry."""

from typing import Any, Optional

from chatgpt2applenotes.exporters.handlers import (
    HandlerRegistry,
    RenderContext,
    handler,
)


def test_render_context_defaults() -> None:
    """RenderContext has correct defaults."""
    ctx = RenderContext()
    assert ctx.render_internals is False


def test_handler_decorator_registers_class() -> None:
    """@handler decorator registers handler class."""
    registry = HandlerRegistry()

    @handler("test_type", target_registry=registry)
    class TestHandler:  # pylint: disable=unused-variable,too-few-public-methods
        """test handler for registration."""

        def render(
            self,
            _content: dict[str, Any],
            _metadata: Optional[dict[str, Any]],
            _ctx: RenderContext,
        ) -> str:
            """renders test content."""
            return "<div>test</div>"

    assert "test_type" in registry._handlers  # pylint: disable=protected-access


def test_handler_decorator_with_multiple_types() -> None:
    """@handler decorator registers multiple content types."""
    registry = HandlerRegistry()

    @handler(["type_a", "type_b"], target_registry=registry)
    class MultiHandler:  # pylint: disable=unused-variable,too-few-public-methods
        """handler for multiple content types."""

        def render(
            self,
            _content: dict[str, Any],
            _metadata: Optional[dict[str, Any]],
            _ctx: RenderContext,
        ) -> str:
            """renders multi-type content."""
            return "<div>multi</div>"

    # pylint: disable=protected-access
    assert "type_a" in registry._handlers
    assert "type_b" in registry._handlers


def test_registry_render_dispatches_to_handler() -> None:
    """registry.render dispatches to correct handler."""
    registry = HandlerRegistry()

    @handler("text", target_registry=registry)
    class TextHandler:  # pylint: disable=unused-variable,too-few-public-methods
        """handler for text content."""

        def render(
            self,
            content: dict[str, Any],
            _metadata: Optional[dict[str, Any]],
            _ctx: RenderContext,
        ) -> str:
            """renders text content."""
            return f"<div>{content.get('value')}</div>"

    ctx = RenderContext()
    result = registry.render({"content_type": "text", "value": "hello"}, None, ctx)
    assert result == "<div>hello</div>"


def test_registry_returns_none_for_unknown_type() -> None:
    """registry.render returns None for unknown content type."""
    registry = HandlerRegistry()
    ctx = RenderContext()
    result = registry.render({"content_type": "unknown"}, None, ctx)
    assert result is None


def test_internal_handler_skipped_without_flag() -> None:
    """internal handler is skipped when render_internals=False."""
    registry = HandlerRegistry()

    @handler("thoughts", internal=True, target_registry=registry)
    class ThoughtsHandler:  # pylint: disable=unused-variable,too-few-public-methods
        """handler for internal thoughts."""

        def render(
            self,
            _content: dict[str, Any],
            _metadata: Optional[dict[str, Any]],
            _ctx: RenderContext,
        ) -> str:
            """renders thoughts content."""
            return "<div>thoughts</div>"

    ctx = RenderContext(render_internals=False)
    result = registry.render({"content_type": "thoughts"}, None, ctx)
    assert result is None


def test_internal_handler_rendered_with_flag() -> None:
    """internal handler renders when render_internals=True."""
    registry = HandlerRegistry()

    @handler("thoughts", internal=True, target_registry=registry)
    class ThoughtsHandler:  # pylint: disable=unused-variable,too-few-public-methods
        """handler for internal thoughts."""

        def render(
            self,
            _content: dict[str, Any],
            _metadata: Optional[dict[str, Any]],
            _ctx: RenderContext,
        ) -> str:
            """renders thoughts content."""
            return "<div>thoughts</div>"

    ctx = RenderContext(render_internals=True)
    result = registry.render({"content_type": "thoughts"}, None, ctx)
    assert result == "<div>thoughts</div>"
