# Apple Notes Renderer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build file-based Apple Notes HTML renderer that converts ChatGPT conversations to Apple Notes-compatible HTML files.

**Architecture:** AppleNotesExporter renders conversations to Apple Notes HTML format with proper structure (div wrappers, spacing, formatting). Supports text, markdown, images, tables, and code blocks. Outputs HTML files that can be manually imported to Apple Notes.

**Tech Stack:** Python 3.9+, markdown-it-py for markdown parsing, existing parser/models

---

## Task 1: Create AppleNotesExporter Structure

**Files:**
- Create: `chatgpt2applenotes/exporters/apple_notes.py`
- Create: `tests/test_apple_notes_exporter.py`

**Step 1: Write failing test for basic file export**

Create `tests/test_apple_notes_exporter.py`:

```python
"""Tests for Apple Notes exporter."""

from pathlib import Path

from chatgpt2applenotes.core.models import Author, Conversation, Message
from chatgpt2applenotes.exporters.apple_notes import AppleNotesExporter


def test_export_to_file_creates_html(tmp_path: Path) -> None:
    """Exporter creates HTML file for conversation."""
    conversation = Conversation(
        id="conv-123",
        title="Test Conversation",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="user"),
                create_time=1234567890.0,
                content={"content_type": "text", "parts": ["Hello"]},
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"

    exporter.export(conversation, str(output_dir))

    output_file = output_dir / "Test_Conversation.html"
    assert output_file.exists()

    html = output_file.read_text(encoding="utf-8")
    assert "<html>" in html
    assert "<body>" in html
    assert "Test Conversation" in html
    assert "Hello" in html
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_apple_notes_exporter.py::test_export_to_file_creates_html -v`

Expected: FAIL with "cannot import name 'AppleNotesExporter'"

**Step 3: Create minimal exporter structure**

Create `chatgpt2applenotes/exporters/apple_notes.py`:

```python
"""Apple Notes exporter for ChatGPT conversations."""

import re
from pathlib import Path
from typing import Literal

from chatgpt2applenotes.core.models import Conversation
from chatgpt2applenotes.exporters.base import Exporter


class AppleNotesExporter(Exporter):
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
        filename = f"{safe_title}.html"

        output_path = Path(destination) / filename

        if dry_run:
            print(f"Would write to: {output_path}")
            return

        # creates output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)

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
        body = f"<div><h1>{conversation.title}</h1></div>"

        # wraps in html/body tags for file target
        if self.target == "file":
            return f"<html><body>{body}</body></html>"
        return body
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_apple_notes_exporter.py::test_export_to_file_creates_html -v`

Expected: PASS

**Step 5: Commit**

```bash
git add chatgpt2applenotes/exporters/apple_notes.py tests/test_apple_notes_exporter.py
git commit -m "feat: add AppleNotesExporter with basic file export"
```

---

## Task 2: Add Conversation Metadata Rendering

**Files:**
- Modify: `chatgpt2applenotes/exporters/apple_notes.py`
- Modify: `tests/test_apple_notes_exporter.py`

**Step 1: Write failing test for metadata**

Add to `tests/test_apple_notes_exporter.py`:

```python
def test_metadata_includes_conversation_id_and_timestamp(tmp_path: Path) -> None:
    """Metadata shows conversation ID and update timestamp."""
    conversation = Conversation(
        id="conv-abc123",
        title="Test",
        create_time=1234567890.0,
        update_time=1736629800.0,  # 2026-01-11 15:30 UTC
        messages=[
            Message(
                id="msg-1",
                author=Author(role="user"),
                create_time=1234567890.0,
                content={"content_type": "text", "parts": ["Hi"]},
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "conv-abc123" in html
    assert "Updated:" in html
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_apple_notes_exporter.py::test_metadata_includes_conversation_id_and_timestamp -v`

Expected: FAIL with assertion errors (metadata not in HTML)

**Step 3: Implement metadata rendering**

Modify `_generate_html()` in `chatgpt2applenotes/exporters/apple_notes.py`:

```python
from datetime import datetime, timezone


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
    parts.append(f"<div><h1>{conversation.title}</h1></div>")

    # conversation metadata
    update_time = datetime.fromtimestamp(
        conversation.update_time, tz=timezone.utc
    ).strftime("%Y-%m-%d %H:%M")
    metadata = f'{conversation.id} | Updated: {update_time}'
    parts.append(
        f'<div style="font-size: x-small; color: gray;">{metadata}</div>'
    )
    parts.append("<div><br></div>")

    # placeholder for messages
    parts.append("<div>Messages will go here</div>")

    body = "".join(parts)

    # wraps in html/body tags for file target
    if self.target == "file":
        return f"<html><body>{body}</body></html>"
    return body
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_apple_notes_exporter.py::test_metadata_includes_conversation_id_and_timestamp -v`

Expected: PASS

**Step 5: Commit**

```bash
git add chatgpt2applenotes/exporters/apple_notes.py tests/test_apple_notes_exporter.py
git commit -m "feat: add conversation metadata rendering"
```

---

## Task 3: Render Message Structure

**Files:**
- Modify: `chatgpt2applenotes/exporters/apple_notes.py`
- Modify: `tests/test_apple_notes_exporter.py`

**Step 1: Write failing test for message rendering**

Add to `tests/test_apple_notes_exporter.py`:

```python
def test_renders_messages_with_author_and_content(tmp_path: Path) -> None:
    """Messages show author role and content."""
    conversation = Conversation(
        id="conv-123",
        title="Test",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="user"),
                create_time=1234567890.0,
                content={"content_type": "text", "parts": ["First message"]},
            ),
            Message(
                id="msg-2",
                author=Author(role="assistant"),
                create_time=1234567895.0,
                content={"content_type": "text", "parts": ["Second message"]},
            ),
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "<h2>User</h2>" in html
    assert "<h2>Assistant</h2>" in html
    assert "First message" in html
    assert "Second message" in html
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_apple_notes_exporter.py::test_renders_messages_with_author_and_content -v`

Expected: FAIL (author headings and messages not rendered)

**Step 3: Implement message rendering**

Modify `_generate_html()` in `chatgpt2applenotes/exporters/apple_notes.py`:

```python
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
    parts.append(f"<div><h1>{conversation.title}</h1></div>")

    # conversation metadata
    update_time = datetime.fromtimestamp(
        conversation.update_time, tz=timezone.utc
    ).strftime("%Y-%m-%d %H:%M")
    metadata = f'{conversation.id} | Updated: {update_time}'
    parts.append(
        f'<div style="font-size: x-small; color: gray;">{metadata}</div>'
    )
    parts.append("<div><br></div>")

    # renders messages
    for message in conversation.messages:
        # author heading
        author_label = message.author.role.capitalize()
        parts.append(f"<div><h2>{author_label}</h2></div>")

        # message ID metadata
        parts.append(
            f'<div style="font-size: x-small; color: gray;">{message.id}</div>'
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
        return text

    # other content types - placeholder
    return "[Unsupported content type]"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_apple_notes_exporter.py::test_renders_messages_with_author_and_content -v`

Expected: PASS

**Step 5: Commit**

```bash
git add chatgpt2applenotes/exporters/apple_notes.py tests/test_apple_notes_exporter.py
git commit -m "feat: render messages with author headings and content"
```

---

## Task 4: Add Markdown Rendering for Text Content

**Files:**
- Modify: `chatgpt2applenotes/exporters/apple_notes.py`
- Modify: `tests/test_apple_notes_exporter.py`

**Step 1: Write failing test for markdown rendering**

Add to `tests/test_apple_notes_exporter.py`:

```python
def test_renders_markdown_in_messages(tmp_path: Path) -> None:
    """Markdown in message content is rendered to Apple Notes HTML."""
    conversation = Conversation(
        id="conv-123",
        title="Test",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="user"),
                create_time=1234567890.0,
                content={
                    "content_type": "text",
                    "parts": ["**bold** and *italic* and `code`"],
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "<b>bold</b>" in html
    assert "<i>italic</i>" in html
    assert "<tt>code</tt>" in html
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_apple_notes_exporter.py::test_renders_markdown_in_messages -v`

Expected: FAIL (raw markdown visible, not rendered tags)

**Step 3: Implement markdown to Apple Notes HTML conversion**

Add new method and modify `_render_message_content()` in `chatgpt2applenotes/exporters/apple_notes.py`:

```python
from markdown_it import MarkdownIt


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


def _markdown_to_apple_notes(self, markdown: str) -> str:
    """
    Converts markdown to Apple Notes HTML format.

    Args:
        markdown: markdown text

    Returns:
        Apple Notes-compatible HTML
    """
    md = MarkdownIt()
    html = md.render(markdown).rstrip("\n")

    # converts markdown-it-py output to Apple Notes format
    # for now, do basic conversions
    # <p>text</p> -> <div>text</div>
    html = html.replace("<p>", "<div>").replace("</p>", "</div>")
    # <strong> -> <b>
    html = html.replace("<strong>", "<b>").replace("</strong>", "</b>")
    # <em> -> <i>
    html = html.replace("<em>", "<i>").replace("</em>", "</i>")
    # <code> -> <tt>
    html = html.replace("<code>", "<tt>").replace("</code>", "</tt>")

    return html
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_apple_notes_exporter.py::test_renders_markdown_in_messages -v`

Expected: PASS

**Step 5: Commit**

```bash
git add chatgpt2applenotes/exporters/apple_notes.py tests/test_apple_notes_exporter.py
git commit -m "feat: render markdown to Apple Notes HTML format"
```

---

## Task 5: Handle Code Blocks

**Files:**
- Modify: `chatgpt2applenotes/exporters/apple_notes.py`
- Modify: `tests/test_apple_notes_exporter.py`

**Step 1: Write failing test for code blocks**

Add to `tests/test_apple_notes_exporter.py`:

```python
def test_renders_code_blocks(tmp_path: Path) -> None:
    """Code blocks are rendered with tt tags."""
    conversation = Conversation(
        id="conv-123",
        title="Test",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="user"),
                create_time=1234567890.0,
                content={
                    "content_type": "text",
                    "parts": ["```python\nprint('hello')\n```"],
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "<tt>" in html
    assert "print('hello')" in html
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_apple_notes_exporter.py::test_renders_code_blocks -v`

Expected: FAIL (code blocks not properly rendered)

**Step 3: Update markdown conversion for code blocks**

Modify `_markdown_to_apple_notes()` in `chatgpt2applenotes/exporters/apple_notes.py`:

```python
def _markdown_to_apple_notes(self, markdown: str) -> str:
    """
    Converts markdown to Apple Notes HTML format.

    Args:
        markdown: markdown text

    Returns:
        Apple Notes-compatible HTML
    """
    md = MarkdownIt()
    html = md.render(markdown).rstrip("\n")

    # converts markdown-it-py output to Apple Notes format
    # <pre><code> -> <div><tt>
    html = html.replace("<pre><code>", "<div><tt>")
    html = html.replace("</code></pre>", "</tt></div>")
    # handles language-specific code blocks
    import re
    html = re.sub(
        r'<pre><code class="language-\w+">', "<div><tt>", html
    )
    # <p>text</p> -> <div>text</div>
    html = html.replace("<p>", "<div>").replace("</p>", "</div>")
    # <strong> -> <b>
    html = html.replace("<strong>", "<b>").replace("</strong>", "</b>")
    # <em> -> <i>
    html = html.replace("<em>", "<i>").replace("</em>", "</i>")
    # <code> -> <tt> (inline code)
    html = html.replace("<code>", "<tt>").replace("</code>", "</tt>")

    return html
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_apple_notes_exporter.py::test_renders_code_blocks -v`

Expected: PASS

**Step 5: Commit**

```bash
git add chatgpt2applenotes/exporters/apple_notes.py tests/test_apple_notes_exporter.py
git commit -m "feat: render code blocks with tt tags"
```

---

## Task 6: Handle Lists

**Files:**
- Modify: `chatgpt2applenotes/exporters/apple_notes.py`
- Modify: `tests/test_apple_notes_exporter.py`

**Step 1: Write failing test for lists**

Add to `tests/test_apple_notes_exporter.py`:

```python
def test_renders_lists(tmp_path: Path) -> None:
    """Lists are rendered as ul/ol with li items."""
    conversation = Conversation(
        id="conv-123",
        title="Test",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="user"),
                create_time=1234567890.0,
                content={
                    "content_type": "text",
                    "parts": ["- Item 1\n- Item 2\n\n1. First\n2. Second"],
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "<ul>" in html
    assert "<li>Item 1</li>" in html
    assert "<ol>" in html
    assert "<li>First</li>" in html
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_apple_notes_exporter.py::test_renders_lists -v`

Expected: PASS (markdown-it-py already renders lists, we just need to keep them)

**Step 3: Verify lists work correctly**

Run: `pytest tests/test_apple_notes_exporter.py::test_renders_lists -v`

If PASS, lists already work. If FAIL, debug and fix.

**Step 4: Commit (if changes needed)**

```bash
git add tests/test_apple_notes_exporter.py
git commit -m "test: verify list rendering works"
```

---

## Task 7: Handle Multimodal Content (Images)

**Files:**
- Modify: `chatgpt2applenotes/exporters/apple_notes.py`
- Modify: `tests/test_apple_notes_exporter.py`

**Step 1: Write failing test for multimodal content with images**

Add to `tests/test_apple_notes_exporter.py`:

```python
def test_renders_multimodal_content_with_images(tmp_path: Path) -> None:
    """Multimodal content renders text and image parts."""
    conversation = Conversation(
        id="conv-123",
        title="Test",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="user"),
                create_time=1234567890.0,
                content={
                    "content_type": "multimodal_text",
                    "parts": [
                        "Here is an image:",
                        {
                            "asset_pointer": "file-service://file-123",
                            "metadata": {
                                "dalle": {
                                    "prompt": "test image",
                                    "seed": 12345,
                                }
                            },
                            "size_bytes": 1000,
                            "width": 100,
                            "height": 100,
                        },
                    ],
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "Here is an image:" in html
    # for now, placeholder for image
    assert "[Image: file-service://file-123]" in html or "[Image" in html
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_apple_notes_exporter.py::test_renders_multimodal_content_with_images -v`

Expected: FAIL (multimodal_text not handled)

**Step 3: Implement multimodal content handling**

Modify `_render_message_content()` in `chatgpt2applenotes/exporters/apple_notes.py`:

```python
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

    if content_type == "multimodal_text":
        return self._render_multimodal_content(message.content)

    # other content types - placeholder
    return "[Unsupported content type]"


def _render_multimodal_content(self, content: dict) -> str:
    """
    Renders multimodal content (text + images).

    Args:
        content: message content dict

    Returns:
        HTML string with text and image placeholders
    """
    parts = content.get("parts") or []
    html_parts = []

    for part in parts:
        if isinstance(part, str):
            # text part - render as markdown
            html_parts.append(self._markdown_to_apple_notes(part))
        elif isinstance(part, dict):
            # image part - placeholder for now
            asset_pointer = part.get("asset_pointer", "unknown")
            html_parts.append(f"<div>[Image: {asset_pointer}]</div>")
            html_parts.append("<div><br></div>")

    return "".join(html_parts)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_apple_notes_exporter.py::test_renders_multimodal_content_with_images -v`

Expected: PASS

**Step 5: Commit**

```bash
git add chatgpt2applenotes/exporters/apple_notes.py tests/test_apple_notes_exporter.py
git commit -m "feat: handle multimodal content with image placeholders"
```

---

## Task 8: Integration Test with Real Conversation

**Files:**
- Modify: `tests/test_apple_notes_exporter.py`

**Step 1: Write integration test with real conversation**

Add to `tests/test_apple_notes_exporter.py`:

```python
import json
from pathlib import Path as PathType

import pytest

from chatgpt2applenotes.core.parser import process_conversation


@pytest.mark.skipif(
    not PathType(
        "/Users/acolomba/Downloads/chatgpt-export-json/ChatGPT-Freezing_Rye_Bread.json"
    ).exists(),
    reason="Real conversation test file not available",
)
def test_export_real_conversation(tmp_path: Path) -> None:
    """Exports real ChatGPT conversation to Apple Notes HTML."""
    json_path = PathType(
        "/Users/acolomba/Downloads/chatgpt-export-json/ChatGPT-Freezing_Rye_Bread.json"
    )

    with open(json_path, encoding="utf-8") as f:
        json_data = json.load(f)

    conversation = process_conversation(json_data)

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    output_file = output_dir / "Freezing_Rye_Bread.html"
    assert output_file.exists()

    html = output_file.read_text(encoding="utf-8")
    assert "<html>" in html
    assert "<body>" in html
    assert conversation.title in html
    assert conversation.id in html
    # has messages
    assert "<h2>" in html
```

**Step 2: Run integration test**

Run: `pytest tests/test_apple_notes_exporter.py::test_export_real_conversation -v`

Expected: PASS (or skip if file not available)

**Step 3: Manual verification**

Open generated HTML file in browser, copy content, paste into Apple Notes to verify formatting.

**Step 4: Commit**

```bash
git add tests/test_apple_notes_exporter.py
git commit -m "test: add integration test with real conversation"
```

---

## Task 9: Add CLI Support (Optional)

**Files:**
- Create: `chatgpt2applenotes/cli.py`
- Create: `tests/test_cli.py`

**Step 1: Write test for CLI**

Create `tests/test_cli.py`:

```python
"""Tests for CLI interface."""

from pathlib import Path
from unittest.mock import patch

from chatgpt2applenotes.cli import main


def test_cli_exports_conversation(tmp_path: Path) -> None:
    """CLI exports conversation file to Apple Notes HTML."""
    json_file = tmp_path / "conversation.json"
    json_file.write_text(
        '{"id": "conv-123", "title": "Test", "create_time": 1234567890.0, '
        '"update_time": 1234567900.0, "mapping": {}}'
    )

    output_dir = tmp_path / "output"

    with patch("sys.argv", ["cli", str(json_file), str(output_dir)]):
        main()

    output_file = output_dir / "Test.html"
    assert output_file.exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py::test_cli_exports_conversation -v`

Expected: FAIL with "cannot import name 'main'"

**Step 3: Implement CLI**

Create `chatgpt2applenotes/cli.py`:

```python
"""CLI interface for ChatGPT to Apple Notes exporter."""

import argparse
import json
import sys
from pathlib import Path

from chatgpt2applenotes.core.parser import process_conversation
from chatgpt2applenotes.exporters.apple_notes import AppleNotesExporter


def main() -> None:
    """runs CLI interface."""
    parser = argparse.ArgumentParser(
        description="Export ChatGPT conversations to Apple Notes HTML"
    )
    parser.add_argument("json_file", help="ChatGPT JSON export file")
    parser.add_argument("output_dir", help="Output directory for HTML files")
    parser.add_argument(
        "--target",
        choices=["file", "notes"],
        default="file",
        help="Export target (default: file)",
    )

    args = parser.parse_args()

    # reads and parses JSON
    with open(args.json_file, encoding="utf-8") as f:
        json_data = json.load(f)

    conversation = process_conversation(json_data)

    # exports to Apple Notes format
    exporter = AppleNotesExporter(target=args.target)
    exporter.export(conversation, args.output_dir)

    print(f"Exported: {conversation.title}")


if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py::test_cli_exports_conversation -v`

Expected: PASS

**Step 5: Add entry point to pyproject.toml**

Add to `pyproject.toml` under `[project.scripts]`:

```toml
[project.scripts]
chatgpt2applenotes = "chatgpt2applenotes.cli:main"
```

**Step 6: Commit**

```bash
git add chatgpt2applenotes/cli.py tests/test_cli.py pyproject.toml
git commit -m "feat: add CLI interface for conversation export"
```

---

## Success Criteria

- ✅ AppleNotesExporter exports conversations to HTML files
- ✅ Markdown rendered to Apple Notes format (bold, italic, code, lists)
- ✅ Multimodal content handled (text + image placeholders)
- ✅ Metadata included (conversation ID, timestamps, message IDs)
- ✅ Integration test with real conversation passes
- ✅ All unit tests pass
- ✅ CLI interface available (optional)

## Next Steps

After Phase 1 completion:
- Manually test generated HTML in Apple Notes
- Implement actual image rendering (base64 or download)
- Add table rendering support
- Phase 2: Direct Apple Notes integration via AppleScript/JXA
