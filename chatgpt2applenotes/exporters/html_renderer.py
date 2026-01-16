"""HTML rendering for Apple Notes export."""

import html as html_lib
import re

from chatgpt2applenotes.core.models import Message

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
