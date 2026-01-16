<!-- markdownlint-disable MD032 MD036 MD031 -->
# Apple Notes Exporter Refactoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Split `apple_notes.py` (1,027 lines) into three focused modules while preserving the public API and ensuring all tests pass.

**Architecture:** Extract AppleScript operations into `applescript.py` (stateless functions) and HTML/markdown rendering into `html_renderer.py` (AppleNotesRenderer class). The main `apple_notes.py` becomes an orchestration layer that delegates to these modules.

**Tech Stack:** Python 3.9+, markdown-it-py, Pillow, AppleScript via subprocess

**Constraint:** Integration tests in `tests/test_e2e_apple_notes.py` MUST pass and CANNOT be modified.

---

## Task 1: Create `applescript.py` with private helpers

**Files:**
- Create: `chatgpt2applenotes/exporters/applescript.py`

**Step 1: Create the module with imports and private helpers**

Create `chatgpt2applenotes/exporters/applescript.py`:

```python
"""AppleScript operations for Apple Notes integration."""

import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


def _parse_folder_path(folder_name: str) -> tuple[str, Optional[str]]:
    """parses folder path into (parent, subfolder) where subfolder is None for flat paths."""
    if "/" in folder_name:
        parts = folder_name.split("/", 1)
        return parts[0], parts[1]
    return folder_name, None


def _escape_applescript(value: str) -> str:
    """escapes string for embedding in AppleScript."""
    return value.replace("\\", "\\\\").replace('"', '\\"')
```

**Step 2: Run linters to verify syntax**

Run: `python -m py_compile chatgpt2applenotes/exporters/applescript.py && echo "OK"`
Expected: OK

**Step 3: Commit**

```bash
git add chatgpt2applenotes/exporters/applescript.py
git commit -m "refactor: add applescript module with private helpers"
```

---

## Task 2: Add folder reference functions to `applescript.py`

**Files:**
- Modify: `chatgpt2applenotes/exporters/applescript.py`

**Step 1: Add `get_folder_ref` function**

Append to `applescript.py`:

```python
def get_folder_ref(folder_name: str) -> str:
    """
    generates AppleScript folder reference for given path.

    Args:
        folder_name: folder path like "Folder" or "Parent/Child"

    Returns:
        AppleScript folder reference like 'folder "Folder"' or
        'folder "Child" of folder "Parent"'
    """
    parent, subfolder = _parse_folder_path(folder_name)
    parent_escaped = _escape_applescript(parent)
    if subfolder:
        subfolder_escaped = _escape_applescript(subfolder)
        return f'folder "{subfolder_escaped}" of folder "{parent_escaped}"'
    return f'folder "{parent_escaped}"'


def get_folder_create_script(folder_name: str) -> str:
    """
    generates AppleScript to create folder (and parent if nested).

    Args:
        folder_name: folder path like "Folder" or "Parent/Child"

    Returns:
        AppleScript snippet to create the folder structure
    """
    parent, subfolder = _parse_folder_path(folder_name)
    parent_escaped = _escape_applescript(parent)

    if subfolder:
        subfolder_escaped = _escape_applescript(subfolder)
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
```

**Step 2: Run linters**

Run: `python -m py_compile chatgpt2applenotes/exporters/applescript.py && echo "OK"`
Expected: OK

**Step 3: Commit**

```bash
git add chatgpt2applenotes/exporters/applescript.py
git commit -m "refactor: add folder reference functions to applescript module"
```

---

## Task 3: Add note read/list/archive functions to `applescript.py`

**Files:**
- Modify: `chatgpt2applenotes/exporters/applescript.py`

**Step 1: Add `read_note_body` function**

Append to `applescript.py`:

```python
def read_note_body(folder: str, conversation_id: str) -> Optional[str]:
    """
    reads note body from Apple Notes by conversation ID.

    Args:
        folder: Apple Notes folder name (supports "Parent/Child" format)
        conversation_id: conversation ID to search for

    Returns:
        note body HTML if found, None otherwise
    """
    folder_ref = get_folder_ref(folder)
    id_escaped = _escape_applescript(conversation_id)

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
```

**Step 2: Add `list_note_conversation_ids` function**

Append to `applescript.py`:

```python
def list_note_conversation_ids(folder: str) -> list[str]:
    """
    lists all conversation IDs from notes in folder.

    Args:
        folder: Apple Notes folder name (supports "Parent/Child" format)

    Returns:
        list of conversation IDs found in notes
    """
    folder_ref = get_folder_ref(folder)

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
```

**Step 3: Add `move_note_to_archive` function**

Append to `applescript.py`:

```python
def move_note_to_archive(folder: str, conversation_id: str) -> bool:
    """
    moves note to Archive subfolder.

    Args:
        folder: Apple Notes folder name (supports "Parent/Child" format)
        conversation_id: conversation ID to find and move

    Returns:
        True if successful, False otherwise
    """
    folder_ref = get_folder_ref(folder)
    id_escaped = _escape_applescript(conversation_id)

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
```

**Step 4: Run linters**

Run: `python -m py_compile chatgpt2applenotes/exporters/applescript.py && echo "OK"`
Expected: OK

**Step 5: Commit**

```bash
git add chatgpt2applenotes/exporters/applescript.py
git commit -m "refactor: add note read/list/archive functions to applescript module"
```

---

## Task 4: Add `append_to_note` function to `applescript.py`

**Files:**
- Modify: `chatgpt2applenotes/exporters/applescript.py`

**Step 1: Add `append_to_note` function**

Append to `applescript.py`:

```python
def append_to_note(folder: str, conversation_id: str, html_content: str) -> bool:
    """
    appends HTML content to existing note.

    Args:
        folder: Apple Notes folder name (supports "Parent/Child" format)
        conversation_id: conversation ID to find
        html_content: HTML to append

    Returns:
        True if successful, False otherwise
    """
    folder_ref = get_folder_ref(folder)
    id_escaped = _escape_applescript(conversation_id)

    # writes HTML to temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as html_file:
        html_file.write(html_content)
        html_path = html_file.name

    html_path_escaped = _escape_applescript(html_path)

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
```

**Step 2: Run linters**

Run: `python -m py_compile chatgpt2applenotes/exporters/applescript.py && echo "OK"`
Expected: OK

**Step 3: Commit**

```bash
git add chatgpt2applenotes/exporters/applescript.py
git commit -m "refactor: add append_to_note function to applescript module"
```

---

## Task 5: Add `write_note` function to `applescript.py`

**Files:**
- Modify: `chatgpt2applenotes/exporters/applescript.py`

**Step 1: Add `write_note` function**

Append to `applescript.py`:

```python
def write_note(
    folder_name: str,
    conversation_id: str,
    html_content: str,
    overwrite: bool,
    image_files: list[str],
) -> None:
    """
    writes or updates note in Apple Notes using AppleScript.

    Args:
        folder_name: folder to store the note in
        conversation_id: conversation ID for finding existing notes
        html_content: HTML content for the note
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
    html_path_escaped = _escape_applescript(html_path)
    id_escaped = _escape_applescript(conversation_id)

    # gets folder reference and creation script (handles nested folders)
    folder_ref = get_folder_ref(folder_name)
    folder_create = get_folder_create_script(folder_name)

    # prepares image attachment commands with deduplication
    # workaround for Apple Notes 4.10-4.11 bug that creates duplicate attachments
    attachment_commands = ""
    if image_files:
        attachment_commands = """
    set attachmentsAdded to 0
"""
        for idx, img_path in enumerate(image_files):
            img_path_escaped = _escape_applescript(img_path)
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
```

**Step 2: Run linters**

Run: `python -m py_compile chatgpt2applenotes/exporters/applescript.py && echo "OK"`
Expected: OK

**Step 3: Commit**

```bash
git add chatgpt2applenotes/exporters/applescript.py
git commit -m "refactor: add write_note function to applescript module"
```

---

## Task 6: Create `html_renderer.py` with constants and helpers

**Files:**
- Create: `chatgpt2applenotes/exporters/html_renderer.py`

**Step 1: Create the module with imports, constants, and LaTeX helpers**

Create `chatgpt2applenotes/exporters/html_renderer.py`:

```python
"""HTML rendering for Apple Notes export."""

import html as html_lib
import re
from typing import Any, Optional, cast

from markdown_it import MarkdownIt

from chatgpt2applenotes.core.models import Conversation, Message

LATEX_PATTERN = re.compile(
    r"(\$\$[\s\S]+?\$\$)|(\$[^\$\n]+?\$)|(\\\[[\s\S]+?\\\])|(\\\([\s\S]+?\\\))",
    re.MULTILINE,
)
FOOTNOTE_PATTERN = re.compile(r"【\d+†\([^)]+\)】")


class AppleNotesRenderer:
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
```

**Step 2: Run linters**

Run: `python -m py_compile chatgpt2applenotes/exporters/html_renderer.py && echo "OK"`
Expected: OK

**Step 3: Commit**

```bash
git add chatgpt2applenotes/exporters/html_renderer.py
git commit -m "refactor: add html_renderer module with constants and helpers"
```

---

## Task 7: Add markdown conversion to `html_renderer.py`

**Files:**
- Modify: `chatgpt2applenotes/exporters/html_renderer.py`

**Step 1: Add `_add_block_spacing` method**

Add after `_tool_message_has_visible_content` in the `AppleNotesRenderer` class:

```python
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
```

**Step 2: Add `_markdown_to_apple_notes` method**

Add after `_add_block_spacing`:

```python
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
```

**Step 3: Run linters**

Run: `python -m py_compile chatgpt2applenotes/exporters/html_renderer.py && echo "OK"`
Expected: OK

**Step 4: Commit**

```bash
git add chatgpt2applenotes/exporters/html_renderer.py
git commit -m "refactor: add markdown conversion to html_renderer module"
```

---

## Task 8: Add content type renderers to `html_renderer.py`

**Files:**
- Modify: `chatgpt2applenotes/exporters/html_renderer.py`

**Step 1: Add content type renderer methods**

Add after `_markdown_to_apple_notes` in the `AppleNotesRenderer` class:

```python
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
```

**Step 2: Run linters**

Run: `python -m py_compile chatgpt2applenotes/exporters/html_renderer.py && echo "OK"`
Expected: OK

**Step 3: Commit**

```bash
git add chatgpt2applenotes/exporters/html_renderer.py
git commit -m "refactor: add content type renderers to html_renderer module"
```

---

## Task 9: Add message rendering dispatcher to `html_renderer.py`

**Files:**
- Modify: `chatgpt2applenotes/exporters/html_renderer.py`

**Step 1: Add `_render_message_content` method**

Add after `_render_tether_browsing_display` in the `AppleNotesRenderer` class:

```python
    def _render_message_content(self, message: Message) -> str:
        """renders message content to Apple Notes HTML."""
        # user messages: escape HTML but don't process markdown
        if message.author.role == "user":
            return self._render_user_content(message)

        content_type = message.content.get("content_type", "text")

        # assistant/tool messages continue through markdown processing
        if content_type == "text":
            return self._render_text_content(message)
        if content_type == "multimodal_text":
            return self._render_multimodal_content(message.content)
        if content_type == "code":
            return self._render_code_content(message)
        if content_type == "execution_output":
            return self._render_execution_output(message)
        if content_type == "tether_quote":
            return self._render_tether_quote(message)
        if content_type == "tether_browsing_display":
            return self._render_tether_browsing_display(message)

        return "[Unsupported content type]"
```

**Step 2: Run linters**

Run: `python -m py_compile chatgpt2applenotes/exporters/html_renderer.py && echo "OK"`
Expected: OK

**Step 3: Commit**

```bash
git add chatgpt2applenotes/exporters/html_renderer.py
git commit -m "refactor: add message rendering dispatcher to html_renderer module"
```

---

## Task 10: Add public render methods to `html_renderer.py`

**Files:**
- Modify: `chatgpt2applenotes/exporters/html_renderer.py`

**Step 1: Add `render_conversation` method**

Add after `_render_message_content` in the `AppleNotesRenderer` class:

```python
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
```

**Step 2: Add `render_append` method**

Add after `render_conversation`:

```python
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
```

**Step 3: Add `extract_last_synced_id` method**

Add after `render_append`:

```python
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
```

**Step 4: Run linters**

Run: `python -m py_compile chatgpt2applenotes/exporters/html_renderer.py && echo "OK"`
Expected: OK

**Step 5: Commit**

```bash
git add chatgpt2applenotes/exporters/html_renderer.py
git commit -m "refactor: add public render methods to html_renderer module"
```

---

## Task 11: Run full test suite on new modules

**Step 1: Run mypy on new modules**

Run: `python -m mypy chatgpt2applenotes/exporters/applescript.py chatgpt2applenotes/exporters/html_renderer.py`
Expected: Success with no errors

**Step 2: Run pylint on new modules**

Run: `python -m pylint chatgpt2applenotes/exporters/applescript.py chatgpt2applenotes/exporters/html_renderer.py`
Expected: No errors (warnings acceptable)

**Step 3: Run ruff on new modules**

Run: `python -m ruff check chatgpt2applenotes/exporters/applescript.py chatgpt2applenotes/exporters/html_renderer.py`
Expected: All checks passed

---

## Task 12: Update `apple_notes.py` to use new modules

**Files:**
- Modify: `chatgpt2applenotes/exporters/apple_notes.py`

**Step 1: Update imports**

Replace the imports section (lines 1-18) with:

```python
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
```

**Step 2: Update `AppleNotesExporter.__init__`**

Replace the `__init__` method with:

```python
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
```

**Step 3: Remove methods that moved to other modules**

Delete these methods from `AppleNotesExporter`:
- `_parse_folder_path` (moved to applescript)
- `_get_author_label` (moved to html_renderer)
- `_tool_message_has_visible_content` (moved to html_renderer)
- `_get_folder_ref` (moved to applescript)
- `_get_folder_create_script` (moved to applescript)
- `_protect_latex` (moved to html_renderer)
- `_restore_latex` (moved to html_renderer)
- `_markdown_to_apple_notes` (moved to html_renderer)
- `_add_block_spacing` (moved to html_renderer)
- `_convert_image_to_png_data_url` (unused, remove)
- `_render_multimodal_content` (moved to html_renderer)
- `_render_user_content` (moved to html_renderer)
- `_render_message_content` (moved to html_renderer)
- `_render_text_content` (moved to html_renderer)
- `_render_code_content` (moved to html_renderer)
- `_render_execution_output` (moved to html_renderer)
- `_render_tether_quote` (moved to html_renderer)
- `_render_tether_browsing_display` (moved to html_renderer)

**Step 4: Update `_generate_html` to delegate to renderer**

Replace `_generate_html` with:

```python
    def _generate_html(self, conversation: Conversation) -> str:
        """generates Apple Notes HTML for conversation."""
        wrap_html = self.target == "file"
        return self._renderer.render_conversation(conversation, wrap_html=wrap_html)
```

**Step 5: Update `_write_to_apple_notes` to delegate to applescript module**

Replace `_write_to_apple_notes` with:

```python
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
```

**Step 6: Update sync-related methods to delegate**

Replace `extract_last_synced_id` with:

```python
    def extract_last_synced_id(self, html: str) -> Optional[str]:
        """extracts last-synced message ID from note footer."""
        return self._renderer.extract_last_synced_id(html)
```

Replace `generate_append_html` with:

```python
    def generate_append_html(
        self, conversation: Conversation, after_message_id: str
    ) -> str:
        """generates HTML for messages after the given message ID."""
        return self._renderer.render_append(conversation, after_message_id)
```

Replace `read_note_body` with:

```python
    def read_note_body(self, folder: str, conversation_id: str) -> Optional[str]:
        """reads note body from Apple Notes by conversation ID."""
        return applescript.read_note_body(folder, conversation_id)
```

Replace `append_to_note` with:

```python
    def append_to_note(
        self, folder: str, conversation_id: str, html_content: str
    ) -> bool:
        """appends HTML content to existing note."""
        return applescript.append_to_note(folder, conversation_id, html_content)
```

Replace `list_note_conversation_ids` with:

```python
    def list_note_conversation_ids(self, folder: str) -> list[str]:
        """lists all conversation IDs from notes in folder."""
        return applescript.list_note_conversation_ids(folder)
```

Replace `move_note_to_archive` with:

```python
    def move_note_to_archive(self, folder: str, conversation_id: str) -> bool:
        """moves note to Archive subfolder."""
        return applescript.move_note_to_archive(folder, conversation_id)
```

**Step 7: Remove `# pylint: disable=too-many-lines` comment**

Delete line 3: `# pylint: disable=too-many-lines  # re-enable after refactoring module size`

**Step 8: Run tests to verify**

Run: `python -m pytest tests/ --ignore=tests/test_e2e_apple_notes.py -v`
Expected: All tests pass

**Step 9: Commit**

```bash
git add chatgpt2applenotes/exporters/apple_notes.py
git commit -m "refactor: update apple_notes.py to delegate to new modules"
```

---

## Task 13: Run full linter and test suite

**Step 1: Run mypy on all exporter modules**

Run: `python -m mypy chatgpt2applenotes/exporters/`
Expected: Success with no errors

**Step 2: Run pylint on all exporter modules**

Run: `python -m pylint chatgpt2applenotes/exporters/`
Expected: No errors

**Step 3: Run full unit test suite**

Run: `python -m pytest tests/ --ignore=tests/test_e2e_apple_notes.py -v`
Expected: All 76+ tests pass

**Step 4: Commit any linter fixes**

If linters made changes:
```bash
git add -A && git commit -m "style: fix linter issues in refactored modules"
```

---

## Task 14: Verify line counts

**Step 1: Count lines in refactored modules**

Run: `wc -l chatgpt2applenotes/exporters/apple_notes.py chatgpt2applenotes/exporters/applescript.py chatgpt2applenotes/exporters/html_renderer.py`

Expected: All modules under 500 lines, total around 1000 lines

---

## Task 15: Final verification and cleanup

**Step 1: Run pre-commit on all files**

Run: `pre-commit run --all-files`
Expected: All checks pass

**Step 2: Run full test suite including e2e (if on macOS with Apple Notes)**

Run: `python -m pytest tests/ -v`
Expected: All tests pass (e2e tests will be skipped if not on macOS)

**Step 3: Create final commit if needed**

```bash
git status
# If any uncommitted changes:
git add -A && git commit -m "refactor: finalize apple notes exporter refactoring"
```

---

## Summary

After completing all tasks:
- `apple_notes.py`: ~250 lines (orchestration only)
- `applescript.py`: ~350 lines (AppleScript operations)
- `html_renderer.py`: ~400 lines (HTML/markdown rendering)
- All existing tests pass without modification
- No `pylint: disable=too-many-lines` needed
