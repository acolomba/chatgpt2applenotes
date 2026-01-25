"""handler registry and base types for content rendering."""

from dataclasses import dataclass
from typing import Any, Callable, Optional, Protocol, TypeVar, Union


@dataclass
class RenderContext:
    """context passed to handlers during rendering."""

    render_internals: bool = False


class ContentHandler(Protocol):  # pylint: disable=too-few-public-methods
    """protocol for content handlers."""

    content_type: Union[str, list[str]]
    internal: bool

    def render(
        self,
        content: dict[str, Any],
        metadata: Optional[dict[str, Any]],
        ctx: RenderContext,
    ) -> str:
        """renders content to HTML."""


class HandlerRegistry:
    """registry for content handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, ContentHandler] = {}

    def register(self, handler_instance: ContentHandler) -> None:
        """registers a handler for its content type(s)."""
        types = (
            handler_instance.content_type
            if isinstance(handler_instance.content_type, list)
            else [handler_instance.content_type]
        )
        for t in types:
            self._handlers[t] = handler_instance

    def render(
        self,
        content: dict[str, Any],
        metadata: Optional[dict[str, Any]],
        ctx: RenderContext,
    ) -> Optional[str]:
        """
        renders content using the appropriate handler.

        Args:
            content: content dict with content_type key
            metadata: optional message metadata
            ctx: render context with flags

        Returns:
            rendered HTML string, or None if unhandled/skipped
        """
        content_type = content.get("content_type", "text")
        handler_instance = self._handlers.get(content_type)

        if not handler_instance:
            return None

        if handler_instance.internal and not ctx.render_internals:
            return None

        return handler_instance.render(content, metadata, ctx)


# global registry
registry = HandlerRegistry()

T = TypeVar("T")


def handler(
    content_type: Union[str, list[str]],
    internal: bool = False,
    target_registry: HandlerRegistry = registry,
) -> Callable[[type[T]], type[T]]:
    """
    decorator to register a content handler.

    Args:
        content_type: content type string or list of strings
        internal: if True, only render when render_internals=True
        target_registry: registry to register with (defaults to global)

    Returns:
        decorator function
    """

    def decorator(cls: type[T]) -> type[T]:
        cls.content_type = content_type  # type: ignore[attr-defined]
        cls.internal = internal  # type: ignore[attr-defined]
        target_registry.register(cls())  # type: ignore[arg-type]
        return cls

    return decorator
