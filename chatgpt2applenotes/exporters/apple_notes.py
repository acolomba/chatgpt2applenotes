"""Apple Notes exporter for ChatGPT conversations."""

import base64
import re
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Literal, Optional

from PIL import Image

from chatgpt2applenotes.core.models import Conversation
from chatgpt2applenotes.exporters import applescript
from chatgpt2applenotes.exporters.base import Exporter
from chatgpt2applenotes.exporters.html_renderer import AppleNotesRenderer


class AppleNotesExporter(Exporter):  # pylint: disable=too-few-public-methods
    """exports conversations to Apple Notes-compatible HTML format."""

    def __init__(
        self,
        target: Literal["file", "notes"] = "file",
        cc_dir: Optional[Path] = None,
    ) -> None:
        """
        Initialize Apple Notes exporter.

        Args:
            target: export target - "file" for HTML files, "notes" for direct integration
            cc_dir: optional directory to save copies of generated HTML
        """
        self.target = target
        self.cc_dir = cc_dir
        self._renderer = AppleNotesRenderer()

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
            destination: output directory path (folder name for notes target)
            dry_run: if True, don't write files
            overwrite: if True, overwrite existing files/notes
        """
        if self.target == "notes":
            self._export_to_notes(conversation, destination, dry_run, overwrite)
        else:
            self._export_to_file(conversation, destination, dry_run, overwrite)

    def _export_to_file(
        self,
        conversation: Conversation,
        destination: str,
        dry_run: bool,
        overwrite: bool,
    ) -> None:
        """exports conversation to HTML file."""
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

    def _save_cc_copy(self, conversation: Conversation, html_content: str) -> None:
        """saves a copy of HTML to cc_dir for debugging."""
        if not self.cc_dir:
            return

        # generates filename from title
        safe_title = re.sub(r"[^\w\s-]", "", conversation.title)
        safe_title = re.sub(r"[-\s]+", "_", safe_title).strip("_")
        filename = f"{safe_title or conversation.id}.html"

        output_path = self.cc_dir / filename
        self.cc_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_content, encoding="utf-8")

    def _export_to_notes(
        self,
        conversation: Conversation,
        folder_name: str,
        dry_run: bool,
        overwrite: bool,
    ) -> None:
        """exports conversation directly to Apple Notes."""
        if dry_run:
            print(f"Would write note '{conversation.title}' to folder '{folder_name}'")
            return

        # checks for existing note
        existing_body = self.read_note_body(folder_name, conversation.id)

        if existing_body and not overwrite:
            # tries append-only sync
            last_synced = self.extract_last_synced_id(existing_body)
            if last_synced:
                # finds new messages and appends
                append_html = self.generate_append_html(conversation, last_synced)
                if append_html:
                    if self.append_to_note(folder_name, conversation.id, append_html):
                        return
                    # falls through to overwrite if append fails
                else:
                    # no new messages
                    return

            # no sync marker found - fall back to overwrite
            overwrite = True

        # collects images and generates HTML content
        image_files: list[str] = []
        html_content = self._generate_html_with_images(conversation, image_files)

        # saves copy to cc_dir if configured
        if self.cc_dir:
            self._save_cc_copy(conversation, html_content)

        # uses AppleScript to create or update note
        self._write_to_apple_notes(
            conversation, html_content, folder_name, overwrite, image_files
        )

    def _write_to_apple_notes(
        self,
        conversation: Conversation,
        html_content: str,
        folder_name: str,
        overwrite: bool,
        image_files: list[str],
    ) -> None:
        """writes or updates note in Apple Notes using AppleScript."""
        applescript.write_note(
            folder_name, conversation.id, html_content, overwrite, image_files
        )

    def _generate_html_with_images(
        self, conversation: Conversation, image_files: list[str]
    ) -> str:
        """
        generates Apple Notes HTML and extracts images to files.

        Args:
            conversation: conversation to render
            image_files: list to populate with image file paths

        Returns:
            HTML string (without inline images)
        """
        # extracts images from messages and saves to temp files
        for message in conversation.messages:
            content_type = message.content.get("content_type", "text")
            if content_type == "multimodal_text":
                parts = message.content.get("parts") or []
                for part in parts:
                    if isinstance(part, dict) and "asset_pointer" in part:
                        asset_pointer = part.get("asset_pointer", "")
                        if asset_pointer and asset_pointer.startswith("data:"):
                            # saves image to temp file
                            img_path = self._save_image_to_file(asset_pointer)
                            if img_path:
                                image_files.append(img_path)

        # generates HTML (without inline images - they'll be added as attachments)
        return self._generate_html(conversation)

    def _save_image_to_file(self, data_url: str) -> Optional[str]:
        """
        saves image from data URL to temporary PNG file.

        Args:
            data_url: image data URL

        Returns:
            path to saved PNG file, or None if failed
        """
        try:
            if ";base64," not in data_url:
                return None

            _, b64_data = data_url.split(";base64,", 1)

            # decodes base64
            img_bytes = base64.b64decode(b64_data)

            # opens image with PIL and converts to PNG
            img = Image.open(BytesIO(img_bytes))

            # saves as PNG to temp file
            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".png", delete=False
            ) as temp_file:
                img.save(temp_file, format="PNG")
                return temp_file.name

        except Exception:
            return None

    def _generate_html(self, conversation: Conversation) -> str:
        """generates Apple Notes HTML for conversation."""
        wrap_html = self.target == "file"
        return self._renderer.render_conversation(conversation, wrap_html=wrap_html)

    def extract_last_synced_id(self, html: str) -> Optional[str]:
        """extracts last-synced message ID from note footer."""
        return self._renderer.extract_last_synced_id(html)

    def generate_append_html(
        self, conversation: Conversation, after_message_id: str
    ) -> str:
        """generates HTML for messages after the given message ID."""
        return self._renderer.render_append(conversation, after_message_id)

    def read_note_body(self, folder: str, conversation_id: str) -> Optional[str]:
        """reads note body from Apple Notes by conversation ID."""
        return applescript.read_note_body(folder, conversation_id)

    def append_to_note(
        self, folder: str, conversation_id: str, html_content: str
    ) -> bool:
        """appends HTML content to existing note."""
        return applescript.append_to_note(folder, conversation_id, html_content)

    def list_note_conversation_ids(self, folder: str) -> list[str]:
        """lists all conversation IDs from notes in folder."""
        return applescript.list_note_conversation_ids(folder)

    def move_note_to_archive(self, folder: str, conversation_id: str) -> bool:
        """moves note to Archive subfolder."""
        return applescript.move_note_to_archive(folder, conversation_id)
