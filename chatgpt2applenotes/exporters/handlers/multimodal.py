"""multimodal text content handler."""

from typing import Any, Optional

from chatgpt2applenotes.exporters.handlers import RenderContext, handler
from chatgpt2applenotes.exporters.handlers.parts import part_registry
from chatgpt2applenotes.exporters.handlers.utils.markdown import markdown_to_html


@handler("multimodal_text")
class MultimodalHandler:  # pylint: disable=too-few-public-methods
    """renders multimodal_text content type by dispatching parts."""

    def render(
        self,
        content: dict[str, Any],
        _metadata: Optional[dict[str, Any]],
        ctx: RenderContext,
    ) -> str:
        """
        renders multimodal content to HTML.

        dispatches string parts to markdown rendering and object parts to the
        part registry based on their content_type.
        """
        parts = content.get("parts") or []
        html_parts = []

        for part in parts:
            if isinstance(part, str):
                # plain text - render as markdown
                html_parts.append(markdown_to_html(part))
            elif isinstance(part, dict):
                # object with content_type - dispatch to part registry
                rendered = part_registry.render(part, ctx)
                if rendered:
                    html_parts.append(rendered)

        return "".join(html_parts)
