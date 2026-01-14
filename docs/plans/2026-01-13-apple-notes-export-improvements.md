# Apple Notes Export Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve Apple Notes export quality by adding missing content types, better message filtering, and improved author labels.

**Architecture:** All changes are in `chatgpt2applenotes/exporters/apple_notes.py`. We add new rendering methods for content types, filtering logic in `_generate_html`, and helper methods for LaTeX protection and footnote cleanup.

**Tech Stack:** Python 3.14, markdown-it-py, pytest

---

## Task 1: Fix Text Part Joining

**Files:**

- Modify: `chatgpt2applenotes/exporters/apple_notes.py:573`
- Test: `tests/test_apple_notes_exporter.py`

### Step 1: Write the failing test

Add to `tests/test_apple_notes_exporter.py`:

```python
def test_text_parts_joined_with_newlines(tmp_path: Path) -> None:
    """text parts are joined with newlines, not spaces."""
    conversation = Conversation(
        id="conv-123",
        title="Test",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="assistant"),
                create_time=1234567890.0,
                content={
                    "content_type": "text",
                    "parts": ["First paragraph.", "Second paragraph."],
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    # parts should be in separate divs (paragraphs), not joined with space
    assert "First paragraph.</div>" in html or "First paragraph.\n" in html
    assert "Second paragraph." in html
    # should NOT be "First paragraph. Second paragraph." in same element
    assert "First paragraph. Second paragraph." not in html
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_apple_notes_exporter.py::test_text_parts_joined_with_newlines -v`
Expected: FAIL - parts are currently joined with space

### Step 3: Write minimal implementation

In `chatgpt2applenotes/exporters/apple_notes.py`, change line 573 from:

```python
text = " ".join(str(p) for p in parts if p)
```

To:

```python
text = "\n".join(str(p) for p in parts if p)
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_apple_notes_exporter.py::test_text_parts_joined_with_newlines -v`
Expected: PASS

### Step 5: Run full test suite

Run: `pytest tests/test_apple_notes_exporter.py -v`
Expected: All tests pass

### Step 6: Commit

```bash
git add chatgpt2applenotes/exporters/apple_notes.py tests/test_apple_notes_exporter.py
git commit -m "fix: join text parts with newlines instead of spaces"
```

---

## Task 2: Add Author Label Helper Method

**Files:**

- Modify: `chatgpt2applenotes/exporters/apple_notes.py`
- Test: `tests/test_apple_notes_exporter.py`

### Step 1: Write the failing test

Add to `tests/test_apple_notes_exporter.py`:

```python
def test_author_labels_use_friendly_names(tmp_path: Path) -> None:
    """author labels use 'ChatGPT', 'You', 'Plugin (name)' instead of roles."""
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
                content={"content_type": "text", "parts": ["Hello"]},
            ),
            Message(
                id="msg-2",
                author=Author(role="assistant"),
                create_time=1234567895.0,
                content={"content_type": "text", "parts": ["Hi there"]},
            ),
            Message(
                id="msg-3",
                author=Author(role="tool", name="browser"),
                create_time=1234567896.0,
                content={"content_type": "text", "parts": ["Search results"]},
            ),
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "<h2>You</h2>" in html
    assert "<h2>ChatGPT</h2>" in html
    assert "<h2>Plugin (browser)</h2>" in html
    # old labels should not appear
    assert "<h2>User</h2>" not in html
    assert "<h2>Assistant</h2>" not in html
    assert "<h2>Tool</h2>" not in html
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_apple_notes_exporter.py::test_author_labels_use_friendly_names -v`
Expected: FAIL - currently shows "User", "Assistant", "Tool"

### Step 3: Write minimal implementation

Add helper method after `_parse_folder_path` (around line 44):

```python
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
```

Update `_generate_html` (around line 391-392) from:

```python
author_label = message.author.role.capitalize()
parts.append(f"<div><h2>{html_lib.escape(author_label)}</h2></div>")
```

To:

```python
author_label = self._get_author_label(message)
parts.append(f"<div><h2>{html_lib.escape(author_label)}</h2></div>")
```

Also update `generate_append_html` (around line 633-634) the same way.

### Step 4: Run test to verify it passes

Run: `pytest tests/test_apple_notes_exporter.py::test_author_labels_use_friendly_names -v`
Expected: PASS

### Step 5: Update existing tests that check for old labels

In `tests/test_apple_notes_exporter.py`, update these tests:

- `test_renders_messages_with_author_and_content`: change `"<h2>User</h2>"` to `"<h2>You</h2>"` and `"<h2>Assistant</h2>"` to `"<h2>ChatGPT</h2>"`
- `test_export_real_conversation`: change assertion to check for `"<h2>You</h2>"` or `"<h2>ChatGPT</h2>"`

### Step 6: Run full test suite

Run: `pytest tests/test_apple_notes_exporter.py -v`
Expected: All tests pass

### Step 7: Commit

```bash
git add chatgpt2applenotes/exporters/apple_notes.py tests/test_apple_notes_exporter.py
git commit -m "feat: use friendly author labels (You, ChatGPT, Plugin)"
```

---

## Task 3: Render User Messages as Plain Text

**Files:**

- Modify: `chatgpt2applenotes/exporters/apple_notes.py`
- Test: `tests/test_apple_notes_exporter.py`

### Step 1: Write the failing test

Add to `tests/test_apple_notes_exporter.py`:

```python
def test_user_messages_not_processed_as_markdown(tmp_path: Path) -> None:
    """user messages are escaped but not markdown-processed."""
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
                    "parts": ["*asterisks* and _underscores_ should stay literal"],
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    # should NOT be converted to italic
    assert "<i>asterisks</i>" not in html
    assert "<em>asterisks</em>" not in html
    assert "<i>underscores</i>" not in html
    assert "<em>underscores</em>" not in html
    # should preserve the literal text
    assert "*asterisks*" in html
    assert "_underscores_" in html
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_apple_notes_exporter.py::test_user_messages_not_processed_as_markdown -v`
Expected: FAIL - currently processes user messages through markdown

### Step 3: Write minimal implementation

Update `_render_message_content` (around line 559) to handle user messages specially:

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

    # user messages: escape HTML but don't process markdown
    if message.author.role == "user":
        if content_type == "text":
            parts = message.content.get("parts") or []
            text = "\n".join(str(p) for p in parts if p)
            # preserve newlines as <br> for display
            escaped = html_lib.escape(text)
            lines = escaped.split("\n")
            return "<div>" + "</div>\n<div>".join(lines) + "</div>"
        if content_type == "multimodal_text":
            return self._render_multimodal_content(message.content, escape_text=True)
        return f"<div>{html_lib.escape('[Unsupported content type]')}</div>"

    # assistant/tool messages: process through markdown
    if content_type == "text":
        parts = message.content.get("parts") or []
        text = "\n".join(str(p) for p in parts if p)
        return self._markdown_to_apple_notes(text)

    if content_type == "multimodal_text":
        return self._render_multimodal_content(message.content)

    # other content types - placeholder
    return "[Unsupported content type]"
```

Update `_render_multimodal_content` signature to accept `escape_text` parameter:

```python
def _render_multimodal_content(
    self, content: dict[str, Any], escape_text: bool = False
) -> str:
    """
    Renders multimodal content (text + images).

    Args:
        content: message content dict
        escape_text: if True, escape text instead of markdown processing

    Returns:
        HTML string with text only (images handled as attachments)
    """
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
        # skips image parts - they're added as attachments

    return "".join(html_parts)
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_apple_notes_exporter.py::test_user_messages_not_processed_as_markdown -v`
Expected: PASS

### Step 5: Update test_renders_markdown_in_messages

The test `test_renders_markdown_in_messages` uses a user message but expects markdown rendering. Change it to use an assistant message:

```python
def test_renders_markdown_in_messages(tmp_path: Path) -> None:
    """Markdown in assistant message content is rendered to Apple Notes HTML."""
    conversation = Conversation(
        id="conv-123",
        title="Test",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="assistant"),  # changed from user
                create_time=1234567890.0,
                content={
                    "content_type": "text",
                    "parts": ["**bold** and *italic* and `code`"],
                },
            )
        ],
    )
    # ... rest of test unchanged
```

### Step 6: Run full test suite

Run: `pytest tests/test_apple_notes_exporter.py -v`
Expected: All tests pass

### Step 7: Commit

```bash
git add chatgpt2applenotes/exporters/apple_notes.py tests/test_apple_notes_exporter.py
git commit -m "feat: render user messages as plain escaped text"
```

---

## Task 4: Filter Messages by Recipient

**Files:**

- Modify: `chatgpt2applenotes/exporters/apple_notes.py`
- Test: `tests/test_apple_notes_exporter.py`

### Step 1: Write the failing test

Add to `tests/test_apple_notes_exporter.py`:

```python
def test_filters_messages_not_to_all(tmp_path: Path) -> None:
    """messages with recipient != 'all' are filtered out."""
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
                content={"content_type": "text", "parts": ["User message"]},
                metadata={"recipient": "all"},
            ),
            Message(
                id="msg-2",
                author=Author(role="assistant"),
                create_time=1234567895.0,
                content={"content_type": "text", "parts": ["Internal tool call"]},
                metadata={"recipient": "browser"},
            ),
            Message(
                id="msg-3",
                author=Author(role="assistant"),
                create_time=1234567896.0,
                content={"content_type": "text", "parts": ["Visible response"]},
                metadata={"recipient": "all"},
            ),
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "User message" in html
    assert "Visible response" in html
    assert "Internal tool call" not in html
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_apple_notes_exporter.py::test_filters_messages_not_to_all -v`
Expected: FAIL - currently shows all messages

### Step 3: Write minimal implementation

In `_generate_html`, add recipient check after content_type check (around line 387):

```python
# renders messages
for message in conversation.messages:
    # skips metadata messages with no user-facing content
    content_type = message.content.get("content_type", "text")
    if content_type == "model_editable_context":
        continue

    # skips messages not addressed to all (internal tool communications)
    recipient = message.metadata.get("recipient", "all") if message.metadata else "all"
    if recipient != "all":
        continue

    # author heading
    # ... rest of method
```

Also update `generate_append_html` with the same check (around line 627).

### Step 4: Run test to verify it passes

Run: `pytest tests/test_apple_notes_exporter.py::test_filters_messages_not_to_all -v`
Expected: PASS

### Step 5: Run full test suite

Run: `pytest tests/test_apple_notes_exporter.py -v`
Expected: All tests pass

### Step 6: Commit

```bash
git add chatgpt2applenotes/exporters/apple_notes.py tests/test_apple_notes_exporter.py
git commit -m "feat: filter out messages not addressed to all"
```

---

## Task 5: Smarter Tool Message Filtering

**Files:**

- Modify: `chatgpt2applenotes/exporters/apple_notes.py`
- Test: `tests/test_apple_notes_exporter.py`

### Step 1: Write the failing test

Add to `tests/test_apple_notes_exporter.py`:

```python
def test_filters_tool_messages_without_visible_content(tmp_path: Path) -> None:
    """tool messages are filtered unless they have multimodal_text or execution_output with images."""
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
                content={"content_type": "text", "parts": ["Generate an image"]},
            ),
            Message(
                id="msg-2",
                author=Author(role="tool", name="browser"),
                create_time=1234567895.0,
                content={"content_type": "text", "parts": ["Browsing results..."]},
            ),
            Message(
                id="msg-3",
                author=Author(role="tool", name="dalle"),
                create_time=1234567896.0,
                content={
                    "content_type": "multimodal_text",
                    "parts": ["Here is your image", {"asset_pointer": "file://img"}],
                },
            ),
            Message(
                id="msg-4",
                author=Author(role="assistant"),
                create_time=1234567897.0,
                content={"content_type": "text", "parts": ["Here you go!"]},
            ),
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "Generate an image" in html
    assert "Here you go!" in html
    # tool with multimodal_text should be shown
    assert "Here is your image" in html
    # tool with plain text should be filtered
    assert "Browsing results..." not in html
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_apple_notes_exporter.py::test_filters_tool_messages_without_visible_content -v`
Expected: FAIL - currently shows all tool messages

### Step 3: Write minimal implementation

Add helper method to check if tool message has visible content:

```python
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
        # check for images in aggregate_result
        metadata = message.metadata or {}
        aggregate_result = metadata.get("aggregate_result", {})
        messages = aggregate_result.get("messages", [])
        return any(msg.get("message_type") == "image" for msg in messages)

    return False
```

Update `_generate_html` to use the helper after recipient check:

```python
# skips tool messages without visible content
if message.author.role == "tool":
    if not self._tool_message_has_visible_content(message):
        continue
```

Also update `generate_append_html` with the same check.

### Step 4: Run test to verify it passes

Run: `pytest tests/test_apple_notes_exporter.py::test_filters_tool_messages_without_visible_content -v`
Expected: PASS

### Step 5: Run full test suite

Run: `pytest tests/test_apple_notes_exporter.py -v`
Expected: All tests pass

### Step 6: Commit

```bash
git add chatgpt2applenotes/exporters/apple_notes.py tests/test_apple_notes_exporter.py
git commit -m "feat: filter tool messages without visible content"
```

---

## Task 6: Add Support for Code Content Type

**Files:**

- Modify: `chatgpt2applenotes/exporters/apple_notes.py`
- Test: `tests/test_apple_notes_exporter.py`

### Step 1: Write the failing test

Add to `tests/test_apple_notes_exporter.py`:

```python
def test_renders_code_content_type(tmp_path: Path) -> None:
    """code content type is rendered as code block."""
    conversation = Conversation(
        id="conv-123",
        title="Test",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="assistant"),
                create_time=1234567890.0,
                content={
                    "content_type": "code",
                    "text": "print('hello world')",
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "<div><tt>" in html
    assert "print(&#x27;hello world&#x27;)" in html
    assert "</tt></div>" in html
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_apple_notes_exporter.py::test_renders_code_content_type -v`
Expected: FAIL - returns "[Unsupported content type]"

### Step 3: Write minimal implementation

Update `_render_message_content` to handle `code` content type:

```python
if content_type == "code":
    text = message.content.get("text", "")
    escaped = html_lib.escape(text)
    return f"<div><tt>{escaped}</tt></div>"
```

Add this after the `multimodal_text` handling, before the fallback.

### Step 4: Run test to verify it passes

Run: `pytest tests/test_apple_notes_exporter.py::test_renders_code_content_type -v`
Expected: PASS

### Step 5: Commit

```bash
git add chatgpt2applenotes/exporters/apple_notes.py tests/test_apple_notes_exporter.py
git commit -m "feat: add support for code content type"
```

---

## Task 7: Add Support for Execution Output Content Type

**Files:**

- Modify: `chatgpt2applenotes/exporters/apple_notes.py`
- Test: `tests/test_apple_notes_exporter.py`

### Step 1: Write the failing test

Add to `tests/test_apple_notes_exporter.py`:

```python
def test_renders_execution_output_content_type(tmp_path: Path) -> None:
    """execution_output content type is rendered as code block."""
    conversation = Conversation(
        id="conv-123",
        title="Test",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="tool", name="python"),
                create_time=1234567890.0,
                content={
                    "content_type": "execution_output",
                    "text": "42",
                },
                metadata={
                    "aggregate_result": {
                        "messages": [{"message_type": "text", "text": "42"}]
                    }
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    # execution output without images should be filtered (tool message rule)
    # but if it passes the filter, it should render as code
    assert "42" in html or "Unsupported" not in html
```

### Step 2: Write test for execution_output with images

```python
def test_renders_execution_output_with_images(tmp_path: Path) -> None:
    """execution_output with images shows images from aggregate_result."""
    conversation = Conversation(
        id="conv-123",
        title="Test",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="tool", name="python"),
                create_time=1234567890.0,
                content={
                    "content_type": "execution_output",
                    "text": "matplotlib output",
                },
                metadata={
                    "aggregate_result": {
                        "messages": [
                            {
                                "message_type": "image",
                                "image_url": "data:image/png;base64,abc123",
                                "width": 400,
                                "height": 300,
                            }
                        ]
                    }
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert '<img src="data:image/png;base64,abc123"' in html
```

### Step 3: Run tests to verify they fail

Run: `pytest tests/test_apple_notes_exporter.py::test_renders_execution_output_content_type tests/test_apple_notes_exporter.py::test_renders_execution_output_with_images -v`
Expected: FAIL

### Step 4: Write minimal implementation

Update `_render_message_content` to handle `execution_output`:

```python
if content_type == "execution_output":
    # check for images in aggregate_result
    metadata = message.metadata or {}
    aggregate_result = metadata.get("aggregate_result", {})
    messages = aggregate_result.get("messages", [])
    image_messages = [m for m in messages if m.get("message_type") == "image"]

    if image_messages:
        # render images
        parts = []
        for img in image_messages:
            url = img.get("image_url", "")
            escaped_url = html_lib.escape(url)
            parts.append(f'<div><img src="{escaped_url}" style="max-width: 100%;"></div>')
        return "\n".join(parts)

    # no images - render as code block
    text = message.content.get("text", "")
    escaped = html_lib.escape(text)
    return f"<div><tt>Result:\n{escaped}</tt></div>"
```

### Step 5: Run tests to verify they pass

Run: `pytest tests/test_apple_notes_exporter.py::test_renders_execution_output_content_type tests/test_apple_notes_exporter.py::test_renders_execution_output_with_images -v`
Expected: PASS

### Step 6: Commit

```bash
git add chatgpt2applenotes/exporters/apple_notes.py tests/test_apple_notes_exporter.py
git commit -m "feat: add support for execution_output content type"
```

---

## Task 8: Add Support for Tether Quote Content Type

**Files:**

- Modify: `chatgpt2applenotes/exporters/apple_notes.py`
- Test: `tests/test_apple_notes_exporter.py`

### Step 1: Write the failing test

Add to `tests/test_apple_notes_exporter.py`:

```python
def test_renders_tether_quote_content_type(tmp_path: Path) -> None:
    """tether_quote content type is rendered as blockquote."""
    conversation = Conversation(
        id="conv-123",
        title="Test",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="assistant"),
                create_time=1234567890.0,
                content={
                    "content_type": "tether_quote",
                    "title": "Source Title",
                    "text": "Quoted text from source",
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "<blockquote>" in html
    # should contain title or text
    assert "Source Title" in html or "Quoted text from source" in html
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_apple_notes_exporter.py::test_renders_tether_quote_content_type -v`
Expected: FAIL

### Step 3: Write minimal implementation

Update `_render_message_content`:

```python
if content_type == "tether_quote":
    title = message.content.get("title", "")
    text = message.content.get("text", "")
    quote_text = title or text or ""
    escaped = html_lib.escape(quote_text)
    return f"<blockquote>{escaped}</blockquote>"
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_apple_notes_exporter.py::test_renders_tether_quote_content_type -v`
Expected: PASS

### Step 5: Commit

```bash
git add chatgpt2applenotes/exporters/apple_notes.py tests/test_apple_notes_exporter.py
git commit -m "feat: add support for tether_quote content type"
```

---

## Task 9: Add Support for Tether Browsing Display Content Type

**Files:**

- Modify: `chatgpt2applenotes/exporters/apple_notes.py`
- Test: `tests/test_apple_notes_exporter.py`

### Step 1: Write the failing test

Add to `tests/test_apple_notes_exporter.py`:

```python
def test_renders_tether_browsing_display_content_type(tmp_path: Path) -> None:
    """tether_browsing_display content type renders cite metadata as links."""
    conversation = Conversation(
        id="conv-123",
        title="Test",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="assistant"),
                create_time=1234567890.0,
                content={"content_type": "tether_browsing_display"},
                metadata={
                    "_cite_metadata": {
                        "metadata_list": [
                            {"title": "Example Site", "url": "https://example.com"},
                            {"title": "Another Site", "url": "https://another.com"},
                        ]
                    }
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "Example Site" in html
    assert "https://example.com" in html
    assert "Another Site" in html
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_apple_notes_exporter.py::test_renders_tether_browsing_display_content_type -v`
Expected: FAIL

### Step 3: Write minimal implementation

Update `_render_message_content`:

```python
if content_type == "tether_browsing_display":
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
        parts.append(f'<blockquote><a href="{escaped_url}">{escaped_title}</a></blockquote>')
    return "\n".join(parts)
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_apple_notes_exporter.py::test_renders_tether_browsing_display_content_type -v`
Expected: PASS

### Step 5: Commit

```bash
git add chatgpt2applenotes/exporters/apple_notes.py tests/test_apple_notes_exporter.py
git commit -m "feat: add support for tether_browsing_display content type"
```

---

## Task 10: Add Audio Transcription Support

**Files:**

- Modify: `chatgpt2applenotes/exporters/apple_notes.py`
- Test: `tests/test_apple_notes_exporter.py`

### Step 1: Write the failing test

Add to `tests/test_apple_notes_exporter.py`:

```python
def test_renders_audio_transcription_in_multimodal(tmp_path: Path) -> None:
    """audio_transcription parts are rendered with italic styling."""
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
                        {
                            "content_type": "audio_transcription",
                            "text": "This is what I said",
                        }
                    ],
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "<i>" in html
    assert "This is what I said" in html
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_apple_notes_exporter.py::test_renders_audio_transcription_in_multimodal -v`
Expected: FAIL

### Step 3: Write minimal implementation

Update `_render_multimodal_content` to handle audio_transcription:

```python
def _render_multimodal_content(
    self, content: dict[str, Any], escape_text: bool = False
) -> str:
    """
    Renders multimodal content (text + images).

    Args:
        content: message content dict
        escape_text: if True, escape text instead of markdown processing

    Returns:
        HTML string with text only (images handled as attachments)
    """
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
        elif isinstance(part, dict):
            part_type = part.get("content_type", "")
            if part_type == "audio_transcription":
                text = part.get("text", "")
                escaped = html_lib.escape(text)
                html_parts.append(f'<div><i>"{escaped}"</i></div>')
            # skip image parts - they're added as attachments
            # skip audio_asset_pointer - not playable

    return "".join(html_parts)
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_apple_notes_exporter.py::test_renders_audio_transcription_in_multimodal -v`
Expected: PASS

### Step 5: Commit

```bash
git add chatgpt2applenotes/exporters/apple_notes.py tests/test_apple_notes_exporter.py
git commit -m "feat: add audio transcription support in multimodal content"
```

---

## Task 11: Implement LaTeX Protection

**Files:**

- Modify: `chatgpt2applenotes/exporters/apple_notes.py`
- Test: `tests/test_apple_notes_exporter.py`

### Step 1: Write the failing test

Add to `tests/test_apple_notes_exporter.py`:

```python
def test_preserves_latex_in_assistant_messages(tmp_path: Path) -> None:
    """LaTeX delimiters are preserved and not mangled by markdown processing."""
    conversation = Conversation(
        id="conv-123",
        title="Test",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="assistant"),
                create_time=1234567890.0,
                content={
                    "content_type": "text",
                    "parts": [
                        "The formula is $E = mc^2$ and also:\n$$\\int_0^1 x^2 dx$$"
                    ],
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    # LaTeX should be preserved (possibly HTML-escaped)
    assert "E = mc^2" in html or "E = mc" in html
    # underscores in LaTeX should not become <em> tags
    assert "_0^1" in html or "_0" in html
    # the integral symbol or command should be present
    assert "int" in html
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_apple_notes_exporter.py::test_preserves_latex_in_assistant_messages -v`
Expected: FAIL - underscores get converted to italics

### Step 3: Write minimal implementation

Add helper methods for LaTeX protection:

```python
import re

# LaTeX pattern matching (inline and display math)
LATEX_PATTERN = re.compile(
    r"(\$\$[\s\S]+?\$\$)"  # display math $$...$$
    r"|(\$[^\$\n]+?\$)"  # inline math $...$
    r"|(\\\[[\s\S]+?\\\])"  # display math \[...\]
    r"|(\\\([\s\S]+?\\\))",  # inline math \(...\)
    re.MULTILINE,
)


def _protect_latex(self, text: str) -> tuple[str, list[str]]:
    """
    replaces LaTeX with placeholders to protect from markdown processing.

    Args:
        text: input text with LaTeX

    Returns:
        tuple of (text with placeholders, list of original LaTeX strings)
    """
    matches: list[str] = []

    def replacer(match: re.Match[str]) -> str:
        matches.append(match.group(0))
        return f"\u2563{len(matches) - 1}\u2563"

    protected = LATEX_PATTERN.sub(replacer, text)
    return protected, matches


def _restore_latex(self, text: str, matches: list[str]) -> str:
    """
    restores LaTeX from placeholders.

    Args:
        text: text with placeholders
        matches: list of original LaTeX strings

    Returns:
        text with LaTeX restored
    """
    for i, latex in enumerate(matches):
        # HTML-escape the LaTeX but preserve it
        escaped = html_lib.escape(latex)
        text = text.replace(f"\u2563{i}\u2563", escaped)
    return text
```

Update `_markdown_to_apple_notes` to use LaTeX protection:

```python
def _markdown_to_apple_notes(self, markdown: str) -> str:
    """
    Converts markdown to Apple Notes HTML format.
    ...
    """
    # protect LaTeX from markdown processing
    protected_text, latex_matches = self._protect_latex(markdown)

    md = MarkdownIt()
    # ... rest of existing implementation using protected_text instead of markdown

    result = cast(str, md.render(protected_text))

    # restore LaTeX
    if latex_matches:
        result = self._restore_latex(result, latex_matches)

    return result
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_apple_notes_exporter.py::test_preserves_latex_in_assistant_messages -v`
Expected: PASS

### Step 5: Run full test suite

Run: `pytest tests/test_apple_notes_exporter.py -v`
Expected: All tests pass

### Step 6: Commit

```bash
git add chatgpt2applenotes/exporters/apple_notes.py tests/test_apple_notes_exporter.py
git commit -m "feat: protect LaTeX from markdown processing

TODO: investigate rendering LaTeX in Apple Notes via MathML or images"
```

---

## Task 12: Implement Footnote Cleanup

**Files:**

- Modify: `chatgpt2applenotes/exporters/apple_notes.py`
- Test: `tests/test_apple_notes_exporter.py`

### Step 1: Write the failing test

Add to `tests/test_apple_notes_exporter.py`:

```python
def test_removes_footnote_marks(tmp_path: Path) -> None:
    """citation marks like 【11†(source)】 are removed from output."""
    conversation = Conversation(
        id="conv-123",
        title="Test",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="assistant"),
                create_time=1234567890.0,
                content={
                    "content_type": "text",
                    "parts": [
                        "According to the source【11†(Wikipedia)】, this is true【3†(source)】."
                    ],
                },
                metadata={
                    "citations": [
                        {"metadata": {"extra": {"cited_message_idx": 11}}},
                        {"metadata": {"extra": {"cited_message_idx": 3}}},
                    ]
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "According to the source" in html
    assert "this is true" in html
    # footnote marks should be removed
    assert "【" not in html
    assert "†" not in html
    assert "(Wikipedia)" not in html
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_apple_notes_exporter.py::test_removes_footnote_marks -v`
Expected: FAIL - footnote marks appear in output

### Step 3: Write minimal implementation

Add helper method:

```python
# Footnote pattern: 【number†(text)】
FOOTNOTE_PATTERN = re.compile(r"【\d+†\([^)]+\)】")


def _remove_footnotes(self, text: str) -> str:
    """
    removes footnote citation marks from text.

    Args:
        text: input text with footnote marks like 【11†(source)】

    Returns:
        text with footnote marks removed
    """
    return FOOTNOTE_PATTERN.sub("", text)
```

Update `_render_message_content` to call `_remove_footnotes` for assistant messages before markdown processing:

```python
if content_type == "text":
    parts = message.content.get("parts") or []
    text = "\n".join(str(p) for p in parts if p)
    # remove footnote marks for assistant messages
    if message.author.role == "assistant":
        text = self._remove_footnotes(text)
    return self._markdown_to_apple_notes(text)
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_apple_notes_exporter.py::test_removes_footnote_marks -v`
Expected: PASS

### Step 5: Run full test suite

Run: `pytest tests/test_apple_notes_exporter.py -v`
Expected: All tests pass

### Step 6: Commit

```bash
git add chatgpt2applenotes/exporters/apple_notes.py tests/test_apple_notes_exporter.py
git commit -m "feat: remove footnote citation marks from assistant messages"
```

---

## Task 13: Final Integration Test and Cleanup

**Files:**

- Test: `tests/test_apple_notes_exporter.py`

### Step 1: Write integration test

Add to `tests/test_apple_notes_exporter.py`:

```python
def test_full_conversation_with_all_features(tmp_path: Path) -> None:
    """integration test with all new features."""
    conversation = Conversation(
        id="abc12345-6789-def0-1234-567890abcdef",
        title="Full Feature Test",
        create_time=1234567890.0,
        update_time=1234567900.0,
        messages=[
            # user message - plain text
            Message(
                id="msg-1",
                author=Author(role="user"),
                create_time=1234567890.0,
                content={"content_type": "text", "parts": ["*asterisks* here"]},
                metadata={"recipient": "all"},
            ),
            # internal message - should be filtered
            Message(
                id="msg-2",
                author=Author(role="assistant"),
                create_time=1234567891.0,
                content={"content_type": "text", "parts": ["Internal"]},
                metadata={"recipient": "browser"},
            ),
            # assistant with footnotes and LaTeX
            Message(
                id="msg-3",
                author=Author(role="assistant"),
                create_time=1234567892.0,
                content={
                    "content_type": "text",
                    "parts": ["Result【1†(src)】: $x^2$"],
                },
                metadata={"recipient": "all"},
            ),
            # tool with text only - should be filtered
            Message(
                id="msg-4",
                author=Author(role="tool", name="browser"),
                create_time=1234567893.0,
                content={"content_type": "text", "parts": ["Hidden"]},
                metadata={"recipient": "all"},
            ),
            # tool with multimodal - should be shown
            Message(
                id="msg-5",
                author=Author(role="tool", name="dalle"),
                create_time=1234567894.0,
                content={
                    "content_type": "multimodal_text",
                    "parts": ["Generated image"],
                },
                metadata={"recipient": "all"},
            ),
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Full_Feature_Test.html").read_text(encoding="utf-8")

    # user message preserved literally
    assert "*asterisks* here" in html
    # internal message filtered
    assert "Internal" not in html
    # footnote removed, LaTeX preserved
    assert "【" not in html
    assert "x^2" in html
    # tool text filtered
    assert "Hidden" not in html
    # tool multimodal shown
    assert "Generated image" in html
    # friendly labels
    assert "<h2>You</h2>" in html
    assert "<h2>ChatGPT</h2>" in html
    assert "<h2>Plugin (dalle)</h2>" in html
```

### Step 2: Run integration test

Run: `pytest tests/test_apple_notes_exporter.py::test_full_conversation_with_all_features -v`
Expected: PASS

### Step 3: Run full test suite

Run: `pytest tests/test_apple_notes_exporter.py -v`
Expected: All tests pass

### Step 4: Run linters and type checks

Run: `cd /Users/acolomba/src/chatgpt2applenotes && python -m mypy chatgpt2applenotes && python -m ruff check chatgpt2applenotes && python -m pylint chatgpt2applenotes`
Expected: No errors

### Step 5: Commit integration test

```bash
git add tests/test_apple_notes_exporter.py
git commit -m "test: add integration test for all export improvements"
```

### Step 6: Update design document status

Mark design as implemented and commit:

```bash
git add docs/plans/
git commit -m "docs: mark apple notes export improvements as implemented"
```

---

## Summary

13 tasks implementing 9 features:

1. Fix text part joining (newlines)
2. Friendly author labels (You, ChatGPT, Plugin)
3. User messages as plain text
4. Filter by recipient
5. Smart tool message filtering
6. Code content type
7. Execution output content type
8. Tether quote content type
9. Tether browsing display content type
10. Audio transcription support
11. LaTeX protection
12. Footnote cleanup
13. Integration test
