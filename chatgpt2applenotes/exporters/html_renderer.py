"""HTML rendering for Apple Notes export."""

import html as html_lib
import re
from typing import Any, Callable, Optional, cast

from markdown_it import MarkdownIt

from chatgpt2applenotes.core.models import Conversation, Message

LATEX_PATTERN = re.compile(
    r"(\$\$[\s\S]+?\$\$)|(\$[^\$\n]+?\$)|(\\\[[\s\S]+?\\\])|(\\\([\s\S]+?\\\))",
    re.MULTILINE,
)
FOOTNOTE_PATTERN = re.compile(r"【\d+†\([^)]+\)】")


class AppleNotesRenderer:  # pylint: disable=too-few-public-methods
    """renders conversations to Apple Notes-compatible HTML."""

    def _protect_latex(self, text: str) -> tuple[str, list[str]]:
        """replaces LaTeX with placeholders to protect from markdown processing."""
        matches: list[str] = []

        def replacer(match: re.Match[str]) -> str:
            matches.append(match.group(0))
            return f"\u2563{len(matches) - 1}\u2563"

        return LATEX_PATTERN.sub(replacer, text), matches

    def _restore_latex(self, text: str, matches: list[str]) -> str:
        """restores LaTeX from placeholders."""
        for i, latex in enumerate(matches):
            text = text.replace(f"\u2563{i}\u2563", html_lib.escape(latex))
        return text

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

    def _add_block_spacing(self, html: str) -> str:
        """adds <div><br></div> between adjacent block elements at top level."""
        # first, clean up empty divs from markdown-it's loose list rendering
        # pattern: <li> or <blockquote> followed by empty <div></div> or <div><br></div>
        html = re.sub(
            r"(<(?:li|blockquote)[^>]*>)\s*<div>(?:<br\s*/?>|\s)*</div>\s*",
            r"\1\n",
            html,
            flags=re.IGNORECASE,
        )

        # use a unique marker to prevent infinite loops
        spacer_marker = "\x00SPACER\x00"

        # block element patterns (closing tag followed by opening tag)
        block_pattern = re.compile(
            r"(</(?:div|ul|ol|blockquote|pre|table|h[1-6])>)"
            r"(\s*)"
            r"(<(?:div|ul|ol|blockquote|pre|table|h[1-6])(?:\s|>))",
            re.IGNORECASE,
        )

        def add_spacer(match: re.Match[str]) -> str:
            return f"{match.group(1)}\n{spacer_marker}\n{match.group(3)}"

        # repeatedly apply until no more changes (handles consecutive blocks)
        prev = ""
        while prev != html:
            prev = html
            html = block_pattern.sub(add_spacer, html)

        # replace markers with actual spacers
        return html.replace(spacer_marker, "<div><br></div>")

    def _markdown_to_apple_notes(self, markdown: str) -> str:
        """converts markdown to Apple Notes HTML format."""
        protected_text, latex_matches = self._protect_latex(markdown)
        md = MarkdownIt()
        # enables table support
        md.enable("table")
        # disables HTML to prevent injection attacks
        md.disable("html_inline")
        md.disable("html_block")

        # customizes renderer to use Apple Notes tags
        # cast to Any for mypy since RendererProtocol doesn't expose renderToken/rules
        renderer: Any = md.renderer
        original_render_token = renderer.renderToken

        def custom_render_token(tokens: Any, idx: int, options: Any, env: Any) -> str:
            """custom token renderer that transforms tags to Apple Notes format."""
            token = tokens[idx]

            # paragraph: p -> div
            if token.tag == "p":
                token.tag = "div"
            # bold: strong -> b
            elif token.tag == "strong":
                token.tag = "b"
            # italic: em -> i
            elif token.tag == "em":
                token.tag = "i"
            # inline code: code -> tt
            elif token.tag == "code":
                token.tag = "tt"

            return cast(str, original_render_token(tokens, idx, options, env))

        renderer.renderToken = custom_render_token

        # custom code block renderer: uses <pre> to preserve whitespace
        def render_code_block(tokens: Any, idx: int, _options: Any, _env: Any) -> str:
            token = tokens[idx]
            escaped = html_lib.escape(token.content)
            return f"<pre>{escaped}</pre>\n"

        renderer.rules["code_block"] = render_code_block
        renderer.rules["fence"] = render_code_block

        # custom image renderer: render images as inline img tags for Apple Notes
        def render_image(tokens: Any, idx: int, _options: Any, _env: Any) -> str:
            token = tokens[idx]
            src = token.attrGet("src") or ""
            # renders as div with img tag, using inline styles for Apple Notes
            escaped_src = html_lib.escape(src)
            return f'<div><img src="{escaped_src}" style="max-width: 100%; max-height: 100%;"></div>\n'

        renderer.rules["image"] = render_image

        result = cast(str, md.render(protected_text))
        result = self._restore_latex(result, latex_matches) if latex_matches else result

        # post-process: add spacing between top-level block elements
        return self._add_block_spacing(result)

    def _render_multimodal_content(
        self, content: dict[str, Any], escape_text: bool = False
    ) -> str:
        """renders multimodal content (text + images) to HTML."""
        parts = content.get("parts") or []
        html_parts = []

        for part in parts:
            if isinstance(part, str):
                if escape_text:
                    escaped = html_lib.escape(part)
                    lines = escaped.split("\n")
                    html_parts.append("<div>" + "</div>\n<div>".join(lines) + "</div>")
                else:
                    html_parts.append(self._markdown_to_apple_notes(part))
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
            text = "\n".join(str(p) for p in parts if p)
            escaped = html_lib.escape(text)
            lines = escaped.split("\n")
            return "<div>" + "</div>\n<div>".join(lines) + "</div>"

        if content_type == "multimodal_text":
            return self._render_multimodal_content(message.content, escape_text=True)

        return f"<div>{html_lib.escape('[Unsupported content type]')}</div>"

    def _render_text_content(self, message: Message) -> str:
        """renders text content type as markdown."""
        parts = message.content.get("parts") or []
        text = "\n".join(str(p) for p in parts if p)
        text = FOOTNOTE_PATTERN.sub("", text)  # removes citation marks
        return self._markdown_to_apple_notes(text)

    def _render_code_content(self, message: Message) -> str:
        """renders code content type as monospace block."""
        text = message.content.get("text", "")
        escaped = html_lib.escape(text)
        return f"<pre>{escaped}</pre>"

    def _render_execution_output(self, message: Message) -> str:
        """renders execution_output content type (images from aggregate_result or text)."""
        metadata = message.metadata or {}
        aggregate_result = metadata.get("aggregate_result", {})
        messages = aggregate_result.get("messages", [])
        image_messages = [m for m in messages if m.get("message_type") == "image"]

        if image_messages:
            parts = []
            for img in image_messages:
                url = img.get("image_url", "")
                escaped_url = html_lib.escape(url)
                parts.append(
                    f'<div><img src="{escaped_url}" style="max-width: 100%;"></div>'
                )
            return "\n".join(parts)

        text = message.content.get("text", "")
        escaped = html_lib.escape(text)
        return f"<div><tt>Result:\n{escaped}</tt></div>"

    def _render_tether_quote(self, message: Message) -> str:
        """renders tether_quote content type (quotes/citations from web browsing)."""
        title = message.content.get("title", "")
        text = message.content.get("text", "")
        quote_text = title or text or ""
        escaped = html_lib.escape(quote_text)
        return f"<blockquote>{escaped}</blockquote>"

    def _render_tether_browsing_display(self, message: Message) -> str:
        """renders tether_browsing_display content type (browsing results with links)."""
        metadata = message.metadata or {}
        cite_metadata = metadata.get("_cite_metadata", {})
        metadata_list = cite_metadata.get("metadata_list", [])

        if not metadata_list:
            return ""

        parts = []
        for item in metadata_list:
            title = item.get("title", "")
            url = item.get("url", "")
            escaped_title = html_lib.escape(title)
            escaped_url = html_lib.escape(url)
            parts.append(
                f'<blockquote><a href="{escaped_url}">{escaped_title}</a></blockquote>'
            )
        return "\n".join(parts)

    def _render_message_content(self, message: Message) -> str:
        """renders message content to Apple Notes HTML."""
        # user messages: escape HTML but don't process markdown
        if message.author.role == "user":
            return self._render_user_content(message)

        content_type = message.content.get("content_type", "text")

        # dispatch table for assistant/tool messages
        renderers: dict[str, Callable[[], str]] = {
            "text": lambda: self._render_text_content(message),
            "multimodal_text": lambda: self._render_multimodal_content(message.content),
            "code": lambda: self._render_code_content(message),
            "execution_output": lambda: self._render_execution_output(message),
            "tether_quote": lambda: self._render_tether_quote(message),
            "tether_browsing_display": lambda: self._render_tether_browsing_display(
                message
            ),
        }

        renderer = renderers.get(content_type)
        return renderer() if renderer else "[Unsupported content type]"

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
