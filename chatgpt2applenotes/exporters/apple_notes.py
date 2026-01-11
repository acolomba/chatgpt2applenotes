"""Apple Notes exporter for ChatGPT conversations."""

import html as html_lib
import re
from pathlib import Path
from typing import Literal

from chatgpt2applenotes.core.models import Conversation
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
        # basic structure for now
        body_parts = [f"<div><h1>{html_lib.escape(conversation.title)}</h1></div>"]

        # adds messages
        for message in conversation.messages:
            if message.content and message.content.get("content_type") == "text":
                parts = message.content.get("parts") or []
                text_parts = [
                    html_lib.escape(str(p)) for p in parts if isinstance(p, str) and p
                ]
                text = " ".join(text_parts)
                if text:
                    body_parts.append(f"<div>{text}</div>")

        body = "".join(body_parts)

        # wraps in html/body tags for file target
        if self.target == "file":
            return f"<html><body>{body}</body></html>"
        return body
