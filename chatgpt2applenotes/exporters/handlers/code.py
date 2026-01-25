"""code content handler."""

import html
from typing import Any, Optional

from chatgpt2applenotes.exporters.handlers import RenderContext, handler


@handler("code")
class CodeHandler:  # pylint: disable=too-few-public-methods
    """renders code content type as pre block."""

    def render(
        self,
        content: dict[str, Any],
        _metadata: Optional[dict[str, Any]],
        _ctx: RenderContext,
    ) -> str:
        """
        renders code content to HTML.

        Args:
            content: content dict with text field
            _metadata: optional message metadata (unused)
            _ctx: render context (unused)

        Returns:
            rendered HTML string
        """
        text = content.get("text", "")
        escaped = html.escape(text)
        return f"<pre>{escaped}</pre>"
