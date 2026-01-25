"""app pairing content handler."""

import html
from typing import Any, Optional

from chatgpt2applenotes.exporters.handlers import RenderContext, handler


@handler("app_pairing_content")
class AppPairingContentHandler:  # pylint: disable=too-few-public-methods
    """renders app_pairing_content content type."""

    def render(
        self,
        content: dict[str, Any],
        _metadata: Optional[dict[str, Any]],
        _ctx: RenderContext,
    ) -> str:
        """
        renders app pairing content to HTML.

        Args:
            content: content dict with workspaces and context_parts
            _metadata: optional message metadata (unused)
            _ctx: render context (unused)

        Returns:
            rendered HTML string
        """
        workspaces = content.get("workspaces", [])
        context_parts = content.get("context_parts", [])

        parts = []

        # render workspace info
        for ws in workspaces:
            app_name = ws.get("app_name", "")
            title = ws.get("title", "")
            escaped_app = html.escape(app_name)
            escaped_title = html.escape(title)
            if app_name and title:
                parts.append(f"<div><b>{escaped_app}</b>: {escaped_title}</div>")
            elif app_name:
                parts.append(f"<div><b>{escaped_app}</b></div>")

        # render context preview (truncated)
        for cp in context_parts:
            text = cp.get("text", "")
            if text:
                preview = text[:200] + "..." if len(text) > 200 else text
                escaped = html.escape(preview)
                parts.append(f"<div><i>{escaped}</i></div>")

        return "\n".join(parts) if parts else ""
