"""HTML exporter matching chatgpt-exporter output."""

import html as html_lib
import re
from pathlib import Path

from chatgpt2applenotes.core.models import Conversation
from chatgpt2applenotes.exporters.base import Exporter


class HTMLExporter(Exporter):  # pylint: disable=too-few-public-methods
    """exports conversations to HTML format (matching TypeScript implementation)."""

    def export(
        self,
        conversation: Conversation,
        destination: str,
        dry_run: bool = False,
        overwrite: bool = False,
    ) -> None:
        """exports conversation to HTML file."""
        # generates filename from title
        # removes/replaces characters that are invalid in filenames
        safe_title = re.sub(r"[^\w\s-]", "", conversation.title)
        safe_title = re.sub(r"[-\s]+", "_", safe_title).strip("_")
        filename = f"ChatGPT-{safe_title}.html"
        output_path = Path(destination) / filename

        if dry_run:
            print(f"Would write to: {output_path}")
            return

        if output_path.exists() and not overwrite:
            print(f"Skipping existing file: {output_path}")
            return

        # generates HTML
        html_content = self._generate_html(conversation)

        # writes to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_content, encoding="utf-8")

    def _generate_html(self, conversation: Conversation) -> str:
        """generates HTML content for conversation."""
        # basic HTML structure - will refine to match reference
        title_escaped = html_lib.escape(conversation.title)

        messages_html = []
        for msg in conversation.messages:
            author_label = msg.author.role.capitalize()
            parts = msg.content.get("parts") or []
            content_text = " ".join(str(p) for p in parts if p)
            content_escaped = html_lib.escape(content_text)

            messages_html.append(
                f"""
                <div class="message">
                    <div class="author">{author_label}</div>
                    <div class="content"><p>{content_escaped}</p></div>
                </div>
            """
            )

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title_escaped}</title>
</head>
<body>
    <h1>{title_escaped}</h1>
    {"".join(messages_html)}
</body>
</html>"""
