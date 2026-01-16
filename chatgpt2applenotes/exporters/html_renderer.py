"""HTML rendering for Apple Notes export."""

import html as html_lib
import re
from typing import Any, cast

from markdown_it import MarkdownIt

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
