"""HTML rendering for Apple Notes export."""

import html as html_lib
import re
from typing import Any, Optional

from chatgpt2applenotes.core.models import Conversation, Message

# imports trigger handler registration
# pylint: disable=unused-import
from chatgpt2applenotes.exporters.handlers import (  # noqa: F401
    RenderContext,
    app_context,
    browsing,
    code,
    errors,
    execution,
    internals,
    multimodal,
    registry,
    text,
)
from chatgpt2applenotes.exporters.handlers.parts import audio  # noqa: F401

# pylint: enable=unused-import


class AppleNotesRenderer:  # pylint: disable=too-few-public-methods
    """renders conversations to Apple Notes-compatible HTML."""

    def __init__(self, render_internals: bool = False) -> None:
        """
        initializes renderer.

        Args:
            render_internals: if True, renders internal content types (thoughts, etc.)
        """
        self.render_internals = render_internals

    def _get_author_label(self, message: Message) -> str:
        """returns friendly author label: 'You', 'ChatGPT', or 'Plugin (name)'."""
        role = message.author.role
        if role == "assistant":
            return "ChatGPT"
        if role == "user":
            return "You"
        if role == "tool":
            name = message.author.name
            return f"Plugin ({name})" if name else "Plugin"
        return role.capitalize()

    def _tool_message_has_visible_content(self, message: Message) -> bool:
        """checks if tool message has user-visible content (multimodal_text or images)."""
        content_type = message.content.get("content_type", "text")

        if content_type == "multimodal_text":
            return True

        if content_type == "execution_output":
            metadata = message.metadata or {}
            aggregate_result = metadata.get("aggregate_result", {})
            messages = aggregate_result.get("messages", [])
            return any(msg.get("message_type") == "image" for msg in messages)

        return False

    def _render_user_multimodal_content(self, content: dict[str, Any]) -> str:
        """renders user multimodal content (text + audio transcriptions) with HTML escaping."""
        parts = content.get("parts") or []
        html_parts = []

        for part in parts:
            if isinstance(part, str):
                escaped = html_lib.escape(part)
                lines = escaped.split("\n")
                html_parts.append("<div>" + "</div>\n<div>".join(lines) + "</div>")
            elif (
                isinstance(part, dict)
                and part.get("content_type") == "audio_transcription"
            ):
                html_parts.append(
                    f'<div><i>"{html_lib.escape(part.get("text", ""))}"</i></div>'
                )
        return "".join(html_parts)

    def _render_user_content(self, message: Message) -> str:
        """
        renders user message content (escaped HTML, no markdown).

        Args:
            message: user message to render

        Returns:
            HTML string
        """
        content_type = message.content.get("content_type", "text")

        if content_type == "text":
            parts = message.content.get("parts") or []
            joined = "\n".join(str(p) for p in parts if p)
            escaped = html_lib.escape(joined)
            lines = escaped.split("\n")
            return "<div>" + "</div>\n<div>".join(lines) + "</div>"

        if content_type == "multimodal_text":
            return self._render_user_multimodal_content(message.content)

        return f"<div>{html_lib.escape('[Unsupported content type]')}</div>"

    def _render_message_content(self, message: Message) -> str:
        """renders message content to Apple Notes HTML."""
        # user messages: escape HTML but don't process markdown
        if message.author.role == "user":
            return self._render_user_content(message)

        # uses handler registry for assistant/tool messages
        ctx = RenderContext(render_internals=self.render_internals)
        rendered = registry.render(message.content, message.metadata, ctx)

        if rendered is not None:
            return rendered

        # fallback for unhandled content types
        return "[Unsupported content type]"

    def render_conversation(
        self, conversation: Conversation, wrap_html: bool = False
    ) -> str:
        """
        generates Apple Notes HTML for conversation.

        Args:
            conversation: conversation to render
            wrap_html: if True, wrap in html/body tags (for file export)

        Returns:
            HTML string
        """
        parts = []

        # conversation title
        parts.append(f"<div><h1>{html_lib.escape(conversation.title)}</h1></div>")
        parts.append("<div><br></div>")

        # renders messages
        for message in conversation.messages:
            # skips metadata messages with no user-facing content
            content_type = message.content.get("content_type", "text")
            if content_type == "model_editable_context":
                continue

            # skips messages not addressed to all (internal tool communications)
            recipient = (
                message.metadata.get("recipient", "all") if message.metadata else "all"
            )
            if recipient != "all":
                continue

            # skips tool messages without visible content
            if (
                message.author.role == "tool"
                and not self._tool_message_has_visible_content(message)
            ):
                continue

            # author heading
            author_label = self._get_author_label(message)
            parts.append(f"<div><h2>{html_lib.escape(author_label)}</h2></div>")
            parts.append("<div><br></div>")

            # message content
            content = self._render_message_content(message)
            parts.append(content)
            parts.append("<div><br></div>")

        # adds footer with conversation ID and last message ID
        if conversation.messages:
            last_msg_id = conversation.messages[-1].id
            parts.append(
                f'<div style="font-size: x-small; color: gray;">'
                f"{html_lib.escape(conversation.id)}:{html_lib.escape(last_msg_id)}</div>"
            )

        body = "".join(parts)

        # wraps in html/body tags for file target
        if wrap_html:
            return f"<html><body>{body}</body></html>"
        return body

    def render_append(self, conversation: Conversation, after_message_id: str) -> str:
        """
        generates HTML for messages after the given message ID.

        Args:
            conversation: conversation with all messages
            after_message_id: only include messages after this ID

        Returns:
            HTML string with new messages and updated sync marker
        """
        # finds index of last synced message
        start_idx = 0
        for i, msg in enumerate(conversation.messages):
            if msg.id == after_message_id:
                start_idx = i + 1
                break

        new_messages = conversation.messages[start_idx:]
        if not new_messages:
            return ""

        parts = []
        for message in new_messages:
            content_type = message.content.get("content_type", "text")
            if content_type == "model_editable_context":
                continue

            # skips messages not addressed to all (internal tool communications)
            recipient = (
                message.metadata.get("recipient", "all") if message.metadata else "all"
            )
            if recipient != "all":
                continue

            # skips tool messages without visible content
            if (
                message.author.role == "tool"
                and not self._tool_message_has_visible_content(message)
            ):
                continue

            # author heading
            author_label = self._get_author_label(message)
            parts.append(f"<div><h2>{html_lib.escape(author_label)}</h2></div>")
            parts.append("<div><br></div>")

            # message content
            content = self._render_message_content(message)
            parts.append(content)
            parts.append("<div><br></div>")

        # adds footer with conversation ID and new last message ID
        last_msg_id = new_messages[-1].id
        parts.append(
            f'<div style="font-size: x-small; color: gray;">'
            f"{html_lib.escape(conversation.id)}:{html_lib.escape(last_msg_id)}</div>"
        )

        return "".join(parts)

    def extract_last_synced_id(self, html: str) -> Optional[str]:
        """
        extracts last-synced message ID from note footer.

        Args:
            html: note body HTML

        Returns:
            message ID if found, None otherwise
        """
        # matches footer format: {conversation_id}:{message_id}
        # conversation ID is UUID, message ID can be various formats
        match = re.search(
            r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}:([^\s<]+)",
            html,
        )
        if match:
            return match.group(1)
        return None
