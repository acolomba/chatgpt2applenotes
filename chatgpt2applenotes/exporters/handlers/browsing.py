"""browsing content handlers for web search results."""

import html
from typing import Any, Optional

from chatgpt2applenotes.exporters.handlers import RenderContext, handler


@handler("tether_quote")
class TetherQuoteHandler:  # pylint: disable=too-few-public-methods
    """renders tether_quote content type as blockquote."""

    def render(
        self,
        content: dict[str, Any],
        _metadata: Optional[dict[str, Any]],
        _ctx: RenderContext,
    ) -> str:
        """
        renders quoted text content to HTML.

        Args:
            content: content dict with text field
            _metadata: optional message metadata (unused)
            _ctx: render context (unused)

        Returns:
            rendered HTML string
        """
        text = content.get("text", "")
        escaped = html.escape(text)
        return f"<blockquote>{escaped}</blockquote>"


@handler("tether_browsing_display")
class TetherBrowsingDisplayHandler:  # pylint: disable=too-few-public-methods
    """renders tether_browsing_display content type with cite links."""

    def render(
        self,
        _content: dict[str, Any],
        metadata: Optional[dict[str, Any]],
        _ctx: RenderContext,
    ) -> str:
        """
        renders browsing display content with citation links.

        Args:
            _content: content dict with result field (unused)
            metadata: optional message metadata with _cite_metadata
            _ctx: render context (unused)

        Returns:
            rendered HTML string
        """
        if not metadata:
            return ""

        cite_metadata = metadata.get("_cite_metadata", {})
        metadata_list = cite_metadata.get("metadata_list", [])

        if not metadata_list:
            return ""

        parts = []
        for item in metadata_list:
            url = item.get("url", "")
            title = item.get("title", url)
            escaped_url = html.escape(url)
            escaped_title = html.escape(title)
            parts.append(
                f'<blockquote><a href="{escaped_url}">{escaped_title}</a></blockquote>'
            )

        return "\n".join(parts)


@handler("sonic_webpage")
class SonicWebpageHandler:  # pylint: disable=too-few-public-methods
    """renders sonic_webpage content type as title link."""

    def render(
        self,
        content: dict[str, Any],
        _metadata: Optional[dict[str, Any]],
        _ctx: RenderContext,
    ) -> str:
        """
        renders webpage content as a titled link.

        Args:
            content: content dict with url and title fields
            _metadata: optional message metadata (unused)
            _ctx: render context (unused)

        Returns:
            rendered HTML string
        """
        url = content.get("url", "")
        title = content.get("title", url)
        escaped_url = html.escape(url)
        escaped_title = html.escape(title)
        return f'<div><a href="{escaped_url}">{escaped_title}</a></div>'
