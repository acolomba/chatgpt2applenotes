"""part registry for multimodal content handlers."""

from typing import Any, Callable, Optional, Protocol, TypeVar, Union

from chatgpt2applenotes.exporters.handlers import RenderContext


class PartHandler(Protocol):  # pylint: disable=too-few-public-methods
    """protocol for multimodal part handlers."""

    content_type: Union[str, list[str]]
    internal: bool

    def render(self, part: dict[str, Any], ctx: RenderContext) -> str:
        """renders part to HTML."""


class PartRegistry:
    """registry for multimodal part handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, PartHandler] = {}

    def register(self, handler_instance: PartHandler) -> None:
        """registers a part handler for its content type(s)."""
        types = (
            handler_instance.content_type
            if isinstance(handler_instance.content_type, list)
            else [handler_instance.content_type]
        )
        for t in types:
            self._handlers[t] = handler_instance

    def render(self, part: dict[str, Any], ctx: RenderContext) -> Optional[str]:
        """
        renders a part using the appropriate handler.

        Args:
            part: part dict with content_type key
            ctx: render context with flags

        Returns:
            rendered HTML string, or None if unhandled/skipped
        """
        content_type = part.get("content_type")
        if not content_type:
            return None

        handler_instance = self._handlers.get(content_type)
        if not handler_instance:
            return None

        if handler_instance.internal and not ctx.render_internals:
            return None

        return handler_instance.render(part, ctx)


# global part registry
part_registry = PartRegistry()

T = TypeVar("T")


def part_handler(
    content_type: Union[str, list[str]],
    internal: bool = False,
    target_registry: PartRegistry = part_registry,
) -> Callable[[type[T]], type[T]]:
    """
    decorator to register a part handler.

    Args:
        content_type: part content type string or list
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
