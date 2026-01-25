"""system error content handler."""

import html
from typing import Any, Optional

from chatgpt2applenotes.exporters.handlers import RenderContext, handler


@handler("system_error")
class SystemErrorHandler:  # pylint: disable=too-few-public-methods
    """renders system_error content type."""

    def render(
        self,
        content: dict[str, Any],
        _metadata: Optional[dict[str, Any]],
        _ctx: RenderContext,
    ) -> str:
        """
        renders system error content to HTML.

        Args:
            content: content dict with name and text fields
            _metadata: optional message metadata (unused)
            _ctx: render context (unused)

        Returns:
            rendered HTML string with warning indicator
        """
        name = content.get("name", "Error")
        text = content.get("text", "")
        escaped_name = html.escape(name)
        escaped_text = html.escape(text)
        return f"<div>\u26a0 <b>{escaped_name}</b>: {escaped_text}</div>"
