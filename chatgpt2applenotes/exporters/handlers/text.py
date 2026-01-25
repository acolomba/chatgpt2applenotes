"""text content handler."""

import re
from typing import Any, Optional

from chatgpt2applenotes.exporters.handlers import RenderContext, handler
from chatgpt2applenotes.exporters.handlers.utils.citations import render_citations
from chatgpt2applenotes.exporters.handlers.utils.markdown import markdown_to_html

FOOTNOTE_PATTERN = re.compile(
    r"[\u3010\u3011\uff3b\uff3d]\d+\u2020\([^)]+\)[\u3010\u3011\uff3b\uff3d]"
)


@handler("text")
class TextHandler:  # pylint: disable=too-few-public-methods
    """renders text content type as markdown."""

    def render(
        self,
        content: dict[str, Any],
        metadata: Optional[dict[str, Any]],
        _ctx: RenderContext,
    ) -> str:
        """
        renders text content to HTML.

        Args:
            content: content dict with parts array
            metadata: optional message metadata with content_references
            _ctx: render context (unused)

        Returns:
            rendered HTML string
        """
        parts = content.get("parts") or []
        text = "\n".join(str(p) for p in parts if p)
        text = FOOTNOTE_PATTERN.sub("", text)
        html = markdown_to_html(text)
        return render_citations(html, metadata)
