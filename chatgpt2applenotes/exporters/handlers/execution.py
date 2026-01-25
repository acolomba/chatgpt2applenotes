"""execution output content handler."""

import html
from typing import Any, Optional

from chatgpt2applenotes.exporters.handlers import RenderContext, handler


@handler("execution_output")
class ExecutionOutputHandler:  # pylint: disable=too-few-public-methods
    """renders execution_output content type."""

    def render(
        self,
        content: dict[str, Any],
        metadata: Optional[dict[str, Any]],
        _ctx: RenderContext,
    ) -> str:
        """
        renders execution output to HTML.

        prefers image output from aggregate_result.messages when available,
        falling back to text output in a pre block.

        Args:
            content: content dict with text field
            metadata: optional message metadata with aggregate_result
            _ctx: render context (unused)

        Returns:
            rendered HTML string
        """
        # check for images in aggregate_result.messages
        if metadata:
            messages = metadata.get("aggregate_result", {}).get("messages", [])
            image_messages = [
                msg for msg in messages if msg.get("message_type") == "image"
            ]
            if image_messages:
                parts = []
                for img in image_messages:
                    url = img.get("image_url", "")
                    escaped_url = html.escape(url)
                    parts.append(
                        f'<div><img src="{escaped_url}" style="max-width: 100%;"></div>'
                    )
                return "\n".join(parts)

        # fallback to text output
        text = content.get("text", "")
        escaped = html.escape(text)
        return f"<pre>{escaped}</pre>"
