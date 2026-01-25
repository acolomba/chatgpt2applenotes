"""internal content handlers (require --render-internals)."""

import html
from typing import Any, Optional

from chatgpt2applenotes.exporters.handlers import RenderContext, handler


@handler("thoughts", internal=True)
class ThoughtsHandler:  # pylint: disable=too-few-public-methods
    """renders thoughts content type."""

    def render(
        self,
        content: dict[str, Any],
        _metadata: Optional[dict[str, Any]],
        _ctx: RenderContext,
    ) -> str:
        """
        renders thoughts content to HTML.

        Args:
            content: content dict with thoughts list
            _metadata: optional message metadata (unused)
            _ctx: render context (unused)

        Returns:
            rendered HTML string with italicized thoughts
        """
        thoughts = content.get("thoughts", [])
        if not thoughts:
            return ""

        parts = []
        for thought in thoughts:
            summary = thought.get("summary", "")
            thought_content = thought.get("content", "")
            escaped_summary = html.escape(summary)
            parts.append(f"<div><i><b>{escaped_summary}</b></i></div>")
            if thought_content:
                escaped_content = html.escape(thought_content)
                parts.append(f"<div><i>{escaped_content}</i></div>")

        return "\n".join(parts)


@handler("reasoning_recap", internal=True)
class ReasoningRecapHandler:  # pylint: disable=too-few-public-methods
    """renders reasoning_recap content type."""

    def render(
        self,
        content: dict[str, Any],
        _metadata: Optional[dict[str, Any]],
        _ctx: RenderContext,
    ) -> str:
        """
        renders reasoning recap content to HTML.

        Args:
            content: content dict with content field
            _metadata: optional message metadata (unused)
            _ctx: render context (unused)

        Returns:
            rendered HTML string with italic indicator
        """
        recap = content.get("content", "")
        if not recap:
            return ""
        escaped = html.escape(recap)
        return f"<div><i>{escaped}</i></div>"


@handler("user_editable_context", internal=True)
class UserEditableContextHandler:  # pylint: disable=too-few-public-methods
    """renders user_editable_context content type."""

    def render(
        self,
        content: dict[str, Any],
        _metadata: Optional[dict[str, Any]],
        _ctx: RenderContext,
    ) -> str:
        """
        renders user editable context to HTML.

        Args:
            content: content dict with user_profile and user_instructions
            _metadata: optional message metadata (unused)
            _ctx: render context (unused)

        Returns:
            rendered HTML string summarizing user profile/instructions
        """
        profile = content.get("user_profile", "")
        instructions = content.get("user_instructions", "")

        if not profile and not instructions:
            return ""

        parts = []
        if profile:
            truncated = profile[:200] + "..." if len(profile) > 200 else profile
            escaped = html.escape(truncated)
            parts.append(f"<div><i>[User Profile] {escaped}</i></div>")
        if instructions:
            truncated = (
                instructions[:200] + "..." if len(instructions) > 200 else instructions
            )
            escaped = html.escape(truncated)
            parts.append(f"<div><i>[User Instructions] {escaped}</i></div>")

        return "\n".join(parts)


@handler("model_editable_context", internal=True)
class ModelEditableContextHandler:  # pylint: disable=too-few-public-methods
    """renders model_editable_context content type."""

    def render(
        self,
        content: dict[str, Any],
        _metadata: Optional[dict[str, Any]],
        _ctx: RenderContext,
    ) -> str:
        """
        renders model editable context to HTML.

        Args:
            content: content dict with model_set_context
            _metadata: optional message metadata (unused)
            _ctx: render context (unused)

        Returns:
            rendered HTML string showing ChatGPT memory note
        """
        context = content.get("model_set_context", "")
        if not context:
            return ""
        escaped = html.escape(context)
        return f"<div><i>[ChatGPT Memory] {escaped}</i></div>"
