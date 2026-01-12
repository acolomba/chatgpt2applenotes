"""Apple Notes exporter for ChatGPT conversations."""

import html as html_lib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from markdown_it import MarkdownIt

from chatgpt2applenotes.core.models import Conversation, Message
from chatgpt2applenotes.exporters.base import Exporter


class AppleNotesExporter(Exporter):  # pylint: disable=too-few-public-methods
    """exports conversations to Apple Notes-compatible HTML format."""

    def __init__(self, target: Literal["file", "notes"] = "file") -> None:
        """
        Initialize Apple Notes exporter.

        Args:
            target: export target - "file" for HTML files, "notes" for direct integration
        """
        self.target = target

    def export(
        self,
        conversation: Conversation,
        destination: str,
        dry_run: bool = False,
        overwrite: bool = True,
    ) -> None:
        """
        Export conversation to Apple Notes format.

        Args:
            conversation: conversation to export
            destination: output directory path
            dry_run: if True, don't write files
            overwrite: if True, overwrite existing files (always True for file target)
        """
        # generates filename from title
        safe_title = re.sub(r"[^\w\s-]", "", conversation.title)
        safe_title = re.sub(r"[-\s]+", "_", safe_title).strip("_")
        filename = f"{safe_title or conversation.id}.html"

        output_path = Path(destination) / filename

        if dry_run:
            print(f"Would write to: {output_path}")
            return

        # creates output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # checks if file exists and should not overwrite
        if output_path.exists() and not overwrite:
            print(f"Skipping existing file: {output_path}")
            return

        # generates HTML content
        html_content = self._generate_html(conversation)

        # writes to file
        output_path.write_text(html_content, encoding="utf-8")

    def _generate_html(self, conversation: Conversation) -> str:
        """
        Generates Apple Notes HTML for conversation.

        Args:
            conversation: conversation to render

        Returns:
            HTML string
        """
        parts = []

        # conversation title
        parts.append(f"<div><h1>{html_lib.escape(conversation.title)}</h1></div>")

        # conversation metadata
        update_time = datetime.fromtimestamp(
            conversation.update_time, tz=timezone.utc
        ).strftime("%Y-%m-%d %H:%M")
        metadata = f"{conversation.id} | Updated: {update_time}"
        parts.append(
            f'<div style="font-size: x-small; color: gray;">{html_lib.escape(metadata)}</div>'
        )
        parts.append("<div><br></div>")

        # renders messages
        for message in conversation.messages:
            # author heading
            author_label = message.author.role.capitalize()
            parts.append(f"<div><h2>{html_lib.escape(author_label)}</h2></div>")

            # message ID metadata
            parts.append(
                f'<div style="font-size: x-small; color: gray;">{html_lib.escape(message.id)}</div>'
            )

            # message content (text only for now)
            content = self._render_message_content(message)
            parts.append(f"<div>{content}</div>")
            parts.append("<div><br></div>")

        body = "".join(parts)

        # wraps in html/body tags for file target
        if self.target == "file":
            return f"<html><body>{body}</body></html>"
        return body

    def _markdown_to_apple_notes(self, markdown: str) -> str:
        """
        Converts markdown to Apple Notes HTML format.

        Transforms markdown-it-py output to Apple Notes-compatible tags:
        - Code blocks: <pre><code> → <div><tt>
        - Paragraphs: <p> → <div>
        - Bold: <strong> → <b>
        - Italic: <em> → <i>
        - Inline code: <code> → <tt>

        Args:
            markdown: markdown text

        Returns:
            Apple Notes-compatible HTML
        """
        md = MarkdownIt()
        # disables HTML to prevent injection attacks
        md.disable("html_inline")
        md.disable("html_block")
        html: str = md.render(markdown).rstrip("\n")

        # converts markdown-it-py output to Apple Notes format
        # IMPORTANT: Process code blocks BEFORE inline code
        # handles language-specific code blocks
        html = re.sub(r'<pre><code class="language-[^"]+">', "<div><tt>", html)
        # <pre><code> -> <div><tt>
        html = html.replace("<pre><code>", "<div><tt>")
        html = html.replace("</code></pre>", "</tt></div>")
        # <p>text</p> -> <div>text</div>
        html = html.replace("<p>", "<div>").replace("</p>", "</div>")
        # <strong> -> <b>
        html = html.replace("<strong>", "<b>").replace("</strong>", "</b>")
        # <em> -> <i>
        html = html.replace("<em>", "<i>").replace("</em>", "</i>")
        # <code> -> <tt> (inline code)
        return html.replace("<code>", "<tt>").replace("</code>", "</tt>")

    def _render_message_content(self, message: Message) -> str:
        """
        Renders message content to Apple Notes HTML.

        Args:
            message: message to render

        Returns:
            HTML string
        """
        content_type = message.content.get("content_type", "text")

        if content_type == "text":
            parts = message.content.get("parts") or []
            text = " ".join(str(p) for p in parts if p)
            return self._markdown_to_apple_notes(text)

        # other content types - placeholder
        return "[Unsupported content type]"
