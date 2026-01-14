"""Apple Notes exporter for ChatGPT conversations."""

import base64
import html as html_lib
import re
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Literal, Optional, cast

from markdown_it import MarkdownIt
from PIL import Image

from chatgpt2applenotes.core.models import Conversation, Message
from chatgpt2applenotes.exporters.base import Exporter

LATEX_PATTERN = re.compile(
    r"(\$\$[\s\S]+?\$\$)|(\$[^\$\n]+?\$)|(\\\[[\s\S]+?\\\])|(\\\([\s\S]+?\\\))",
    re.MULTILINE,
)
FOOTNOTE_PATTERN = re.compile(r"【\d+†\([^)]+\)】")


class AppleNotesExporter(Exporter):  # pylint: disable=too-few-public-methods
    """exports conversations to Apple Notes-compatible HTML format."""

    def __init__(self, target: Literal["file", "notes"] = "file") -> None:
        """
        Initialize Apple Notes exporter.

        Args:
            target: export target - "file" for HTML files, "notes" for direct integration
        """
        self.target = target

    def _parse_folder_path(self, folder_name: str) -> tuple[str, Optional[str]]:
        """
        parses folder path into parent and subfolder components.

        Args:
            folder_name: folder path like "Folder" or "Parent/Child"

        Returns:
            tuple of (parent_folder, subfolder) where subfolder is None for flat paths
        """
        if "/" in folder_name:
            parts = folder_name.split("/", 1)
            return parts[0], parts[1]
        return folder_name, None

    def _get_author_label(self, message: Message) -> str:
        """
        returns friendly author label for message.

        Args:
            message: message to get label for

        Returns:
            'You' for user, 'ChatGPT' for assistant, 'Plugin (name)' for tools
        """
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
        """
        checks if tool message has user-visible content.

        Tool messages are only shown if they contain:
        - multimodal_text (e.g., DALL-E generated images)
        - execution_output with images in metadata.aggregate_result

        Args:
            message: tool message to check

        Returns:
            True if message should be shown, False otherwise
        """
        content_type = message.content.get("content_type", "text")

        if content_type == "multimodal_text":
            return True

        if content_type == "execution_output":
            metadata = message.metadata or {}
            aggregate_result = metadata.get("aggregate_result", {})
            messages = aggregate_result.get("messages", [])
            return any(msg.get("message_type") == "image" for msg in messages)

        return False

    def _get_folder_ref(self, folder_name: str) -> str:
        """
        generates AppleScript folder reference for given path.

        Args:
            folder_name: folder path like "Folder" or "Parent/Child"

        Returns:
            AppleScript folder reference like 'folder "Folder"' or
            'folder "Child" of folder "Parent"'
        """
        parent, subfolder = self._parse_folder_path(folder_name)
        parent_escaped = parent.replace("\\", "\\\\").replace('"', '\\"')
        if subfolder:
            subfolder_escaped = subfolder.replace("\\", "\\\\").replace('"', '\\"')
            return f'folder "{subfolder_escaped}" of folder "{parent_escaped}"'
        return f'folder "{parent_escaped}"'

    def _get_folder_create_script(self, folder_name: str) -> str:
        """
        generates AppleScript to create folder (and parent if nested).

        Args:
            folder_name: folder path like "Folder" or "Parent/Child"

        Returns:
            AppleScript snippet to create the folder structure
        """
        parent, subfolder = self._parse_folder_path(folder_name)
        parent_escaped = parent.replace("\\", "\\\\").replace('"', '\\"')

        if subfolder:
            subfolder_escaped = subfolder.replace("\\", "\\\\").replace('"', '\\"')
            return f"""
    if not (exists folder "{parent_escaped}") then
        make new folder with properties {{name:"{parent_escaped}"}}
    end if
    if not (exists folder "{subfolder_escaped}" of folder "{parent_escaped}") then
        make new folder at folder "{parent_escaped}" with properties {{name:"{subfolder_escaped}"}}
    end if"""
        return f"""
    if not (exists folder "{parent_escaped}") then
        make new folder with properties {{name:"{parent_escaped}"}}
    end if"""

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
        """
        writes or updates note in Apple Notes using AppleScript.

        Args:
            conversation: conversation to write
            html_content: HTML content for the note
            folder_name: folder to store the note in
            overwrite: if True, update existing note with same ID
            image_files: list of image file paths to add as attachments
        """
        # writes HTML to temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", delete=False, encoding="utf-8"
        ) as html_file:
            html_file.write(html_content)
            html_path = html_file.name

        # escapes quotes and backslashes for AppleScript
        html_path_escaped = html_path.replace("\\", "\\\\").replace('"', '\\"')
        id_escaped = conversation.id.replace("\\", "\\\\").replace('"', '\\"')

        # gets folder reference and creation script (handles nested folders)
        folder_ref = self._get_folder_ref(folder_name)
        folder_create = self._get_folder_create_script(folder_name)

        # prepares image attachment commands with deduplication
        # workaround for Apple Notes 4.10-4.11 bug that creates duplicate attachments
        attachment_commands = ""
        if image_files:
            attachment_commands = """
    set attachmentsAdded to 0
"""
            for idx, img_path in enumerate(image_files):
                img_path_escaped = img_path.replace("\\", "\\\\").replace('"', '\\"')
                attachment_commands += f"""
    set imgFile{idx} to POSIX file "{img_path_escaped}"
    make new attachment at theNote with data imgFile{idx}
    set attachmentsAdded to attachmentsAdded + 1
    if ((count attachments of theNote) > attachmentsAdded) then
        delete last attachment of theNote
    end if
"""

        if overwrite:
            # tries to find and delete existing note, then creates new one
            applescript = f"""
tell application "Notes"
    -- creates folder if it doesn't exist
{folder_create}

    set targetFolder to {folder_ref}

    -- searches for and deletes existing note containing conversation ID
    set notesList to every note of targetFolder
    repeat with aNote in notesList
        if body of aNote contains "{id_escaped}" then
            delete aNote
            exit repeat
        end if
    end repeat

    -- reads HTML from file
    set htmlContent to read POSIX file "{html_path_escaped}" as «class utf8»

    -- creates new note (title derived from H1 heading)
    set theNote to make new note at targetFolder with properties {{body:htmlContent}}

    -- adds image attachments (with deduplication for Apple Notes 4.10-4.11 bug)
{attachment_commands}
end tell
"""
        else:
            # creates new note without checking for existing
            applescript = f"""
tell application "Notes"
    -- creates folder if it doesn't exist
{folder_create}

    -- reads HTML from file
    set htmlContent to read POSIX file "{html_path_escaped}" as «class utf8»

    -- creates note (title derived from H1 heading)
    set theNote to make new note at {folder_ref} with properties {{body:htmlContent}}

    -- adds image attachments (with deduplication for Apple Notes 4.10-4.11 bug)
{attachment_commands}
end tell
"""

        # executes AppleScript via temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".scpt", delete=False
        ) as script_file:
            script_file.write(applescript)
            script_path = script_file.name

        try:
            subprocess.run(
                ["osascript", script_path],
                check=True,
                capture_output=True,
                text=True,
            )
        finally:
            # cleans up temporary files
            Path(script_path).unlink(missing_ok=True)
            Path(html_path).unlink(missing_ok=True)
            # cleans up image files
            for img_path in image_files:
                Path(img_path).unlink(missing_ok=True)

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
        if self.target == "file":
            return f"<html><body>{body}</body></html>"
        return body

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

            # paragraph: p → div
            if token.tag == "p":
                token.tag = "div"
            # bold: strong → b
            elif token.tag == "strong":
                token.tag = "b"
            # italic: em → i
            elif token.tag == "em":
                token.tag = "i"
            # inline code: code → tt
            elif token.tag == "code":
                token.tag = "tt"
            # headers: add br before and after
            elif token.tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                if token.nesting == 1:  # opening tag
                    return f"<br>\n{original_render_token(tokens, idx, options, env)}"
                if token.nesting == -1:  # closing tag
                    return f"{original_render_token(tokens, idx, options, env)}\n<br>"

            return cast(str, original_render_token(tokens, idx, options, env))

        renderer.renderToken = custom_render_token

        # custom code block renderer: pre/code → div/tt
        def render_code_block(tokens: Any, idx: int, _options: Any, _env: Any) -> str:
            token = tokens[idx]
            return f"<div><tt>{html_lib.escape(token.content)}</tt></div>\n"

        def render_fence(tokens: Any, idx: int, _options: Any, _env: Any) -> str:
            token = tokens[idx]
            return f"<div><tt>{html_lib.escape(token.content)}</tt></div>\n"

        renderer.rules["code_block"] = render_code_block
        renderer.rules["fence"] = render_fence

        # custom image renderer: render images as inline img tags for Apple Notes
        def render_image(tokens: Any, idx: int, _options: Any, _env: Any) -> str:
            token = tokens[idx]
            src = token.attrGet("src") or ""
            # renders as div with img tag, using inline styles for Apple Notes
            escaped_src = html_lib.escape(src)
            return f'<div><img src="{escaped_src}" style="max-width: 100%; max-height: 100%;"></div>\n'

        renderer.rules["image"] = render_image

        result = cast(str, md.render(protected_text))
        return self._restore_latex(result, latex_matches) if latex_matches else result

    def _convert_image_to_png_data_url(self, data_url: str) -> str:
        """converts image data URL to PNG format for Apple Notes compatibility."""
        if not data_url.startswith("data:"):
            return data_url

        try:
            # extracts base64 data
            if ";base64," not in data_url:
                return data_url

            _, b64_data = data_url.split(";base64,", 1)

            # decodes base64
            img_bytes = base64.b64decode(b64_data)

            # opens image with PIL and converts to PNG
            img = Image.open(BytesIO(img_bytes))

            # converts to PNG in memory
            png_buffer = BytesIO()
            img.save(png_buffer, format="PNG")
            png_bytes = png_buffer.getvalue()

            # encodes as base64
            png_b64 = base64.b64encode(png_bytes).decode("ascii")

            return f"data:image/png;base64,{png_b64}"

        except Exception:
            # if conversion fails, return original
            return data_url

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

    def _render_message_content(self, message: Message) -> str:
        """renders message content to Apple Notes HTML."""
        # user messages: escape HTML but don't process markdown
        if message.author.role == "user":
            return self._render_user_content(message)

        content_type = message.content.get("content_type", "text")

        # assistant/tool messages continue through markdown processing
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

    def _render_text_content(self, message: Message) -> str:
        """renders text content type as markdown."""
        parts = message.content.get("parts") or []
        text = "\n".join(str(p) for p in parts if p)
        text = FOOTNOTE_PATTERN.sub("", text)  # removes citation marks
        return self._markdown_to_apple_notes(text)

    def _render_code_content(self, message: Message) -> str:
        """renders code content type as monospace block."""
        text = message.content.get("text", "")
        return f"<div><tt>{html_lib.escape(text)}</tt></div>"

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

    def generate_append_html(
        self, conversation: Conversation, after_message_id: str
    ) -> str:
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

    def read_note_body(self, folder: str, conversation_id: str) -> Optional[str]:
        """
        reads note body from Apple Notes by conversation ID.

        Args:
            folder: Apple Notes folder name (supports "Parent/Child" format)
            conversation_id: conversation ID to search for

        Returns:
            note body HTML if found, None otherwise
        """
        folder_ref = self._get_folder_ref(folder)
        id_escaped = conversation_id.replace("\\", "\\\\").replace('"', '\\"')

        applescript = f"""
tell application "Notes"
    if not (exists {folder_ref}) then
        return ""
    end if

    set notesList to every note of {folder_ref}
    repeat with aNote in notesList
        if body of aNote contains "{id_escaped}" then
            return body of aNote
        end if
    end repeat
    return ""
end tell
"""
        try:
            result = subprocess.run(
                ["osascript", "-e", applescript],
                check=True,
                capture_output=True,
                text=True,
            )
            body = result.stdout.strip()
            return body if body else None
        except subprocess.CalledProcessError:
            return None

    def append_to_note(
        self, folder: str, conversation_id: str, html_content: str
    ) -> bool:
        """
        appends HTML content to existing note.

        Args:
            folder: Apple Notes folder name (supports "Parent/Child" format)
            conversation_id: conversation ID to find
            html_content: HTML to append

        Returns:
            True if successful, False otherwise
        """
        folder_ref = self._get_folder_ref(folder)
        id_escaped = conversation_id.replace("\\", "\\\\").replace('"', '\\"')

        # writes HTML to temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", delete=False, encoding="utf-8"
        ) as html_file:
            html_file.write(html_content)
            html_path = html_file.name

        html_path_escaped = html_path.replace("\\", "\\\\").replace('"', '\\"')

        applescript = f"""
tell application "Notes"
    if not (exists {folder_ref}) then
        return false
    end if

    set htmlContent to read POSIX file "{html_path_escaped}" as «class utf8»

    set notesList to every note of {folder_ref}
    repeat with aNote in notesList
        if body of aNote contains "{id_escaped}" then
            set oldBody to body of aNote
            set body of aNote to oldBody & htmlContent
            return true
        end if
    end repeat
    return false
end tell
"""
        try:
            result = subprocess.run(
                ["osascript", "-e", applescript],
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip() == "true"
        except subprocess.CalledProcessError:
            return False
        finally:
            Path(html_path).unlink(missing_ok=True)

    def list_note_conversation_ids(self, folder: str) -> list[str]:
        """
        lists all conversation IDs from notes in folder.

        Args:
            folder: Apple Notes folder name (supports "Parent/Child" format)

        Returns:
            list of conversation IDs found in notes
        """
        folder_ref = self._get_folder_ref(folder)

        applescript = f"""
tell application "Notes"
    if not (exists {folder_ref}) then
        return ""
    end if

    set notesList to every note of {folder_ref}
    set result to ""
    repeat with aNote in notesList
        set result to result & (body of aNote) & "|||SEPARATOR|||"
    end repeat
    return result
end tell
"""
        try:
            result = subprocess.run(
                ["osascript", "-e", applescript],
                check=True,
                capture_output=True,
                text=True,
            )
            output = result.stdout.strip()
            if not output:
                return []

            # extracts conversation IDs from note bodies
            # looks for UUID-format conversation ID followed by colon in footer
            conv_ids = []
            for body in output.split("|||SEPARATOR|||"):
                # matches footer format: {conversation_id}:{message_id}
                match = re.search(
                    r"([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}):",
                    body,
                )
                if match:
                    conv_ids.append(match.group(1))

            return conv_ids
        except subprocess.CalledProcessError:
            return []

    def move_note_to_archive(self, folder: str, conversation_id: str) -> bool:
        """
        moves note to Archive subfolder.

        Args:
            folder: Apple Notes folder name (supports "Parent/Child" format)
            conversation_id: conversation ID to find and move

        Returns:
            True if successful, False otherwise
        """
        folder_ref = self._get_folder_ref(folder)
        id_escaped = conversation_id.replace("\\", "\\\\").replace('"', '\\"')

        applescript = f"""
tell application "Notes"
    if not (exists {folder_ref}) then
        return false
    end if

    -- creates Archive subfolder if needed
    if not (exists folder "Archive" of {folder_ref}) then
        make new folder at {folder_ref} with properties {{name:"Archive"}}
    end if

    set notesList to every note of {folder_ref}
    repeat with aNote in notesList
        if body of aNote contains "{id_escaped}" then
            move aNote to folder "Archive" of {folder_ref}
            return true
        end if
    end repeat
    return false
end tell
"""
        try:
            result = subprocess.run(
                ["osascript", "-e", applescript],
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip() == "true"
        except subprocess.CalledProcessError:
            return False
