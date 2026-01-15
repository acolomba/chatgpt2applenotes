# Code Block Line Breaks Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Preserve line breaks in code blocks so multiline code renders correctly in Apple Notes.

**Architecture:** The current `render_fence` and `render_code_block` functions output `<div><tt>content</tt></div>` which collapses whitespace. We'll convert newlines to `<br>` tags within the `<tt>` element to preserve line structure.

**Tech Stack:** Python, markdown-it-py, pytest

---

## Task 1: Add Failing Test for Multiline Code Block Rendering

**Files:**

- Modify: `tests/test_apple_notes_exporter.py`

### Step 1: Write the failing test

Add this test after the existing `test_renders_code_blocks` test (around line 265):

```python
def test_renders_code_blocks_with_linebreaks(tmp_path: Path) -> None:
    """multiline code blocks preserve line breaks."""
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
                    "parts": ["```python\ndef hello():\n    print('hi')\n    return 42\n```"],
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    # line breaks should be preserved as <br> tags
    assert "<br>" in html or "<br/>" in html or "<br />" in html
    # each line should be present
    assert "def hello():" in html
    assert "print" in html
    assert "return 42" in html
```

### Step 2: Run test to verify it fails

Run: `cd /Users/acolomba/src/chatgpt2applenotes/.worktrees/code-block-linebreaks && uv run pytest tests/test_apple_notes_exporter.py::test_renders_code_blocks_with_linebreaks -v`

Expected: FAIL - no `<br>` tags in output

---

## Task 2: Implement Line Break Preservation in Fenced Code Blocks

**Files:**

- Modify: `chatgpt2applenotes/exporters/apple_notes.py:533-542`

### Step 1: Update render_code_block function

Replace the `render_code_block` function (around line 533) with:

```python
        def render_code_block(tokens: Any, idx: int, _options: Any, _env: Any) -> str:
            token = tokens[idx]
            escaped = html_lib.escape(token.content)
            # converts newlines to <br> for Apple Notes
            with_breaks = escaped.replace("\n", "<br>")
            return f"<div><tt>{with_breaks}</tt></div>\n"
```

### Step 2: Update render_fence function

Replace the `render_fence` function (around line 537) with:

```python
        def render_fence(tokens: Any, idx: int, _options: Any, _env: Any) -> str:
            token = tokens[idx]
            escaped = html_lib.escape(token.content)
            # converts newlines to <br> for Apple Notes
            with_breaks = escaped.replace("\n", "<br>")
            return f"<div><tt>{with_breaks}</tt></div>\n"
```

### Step 3: Run test to verify it passes

Run: `cd /Users/acolomba/src/chatgpt2applenotes/.worktrees/code-block-linebreaks && uv run pytest tests/test_apple_notes_exporter.py::test_renders_code_blocks_with_linebreaks -v`

Expected: PASS

### Step 4: Run all tests to ensure no regressions

Run: `cd /Users/acolomba/src/chatgpt2applenotes/.worktrees/code-block-linebreaks && uv run pytest -v`

Expected: All tests pass

### Step 5: Commit

```bash
cd /Users/acolomba/src/chatgpt2applenotes/.worktrees/code-block-linebreaks
git add tests/test_apple_notes_exporter.py chatgpt2applenotes/exporters/apple_notes.py
git commit -m "feat: preserve line breaks in code blocks

Converts newlines to <br> tags in fenced code blocks and indented
code blocks for proper rendering in Apple Notes.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Add Test and Fix for Code Content Type

**Files:**

- Modify: `tests/test_apple_notes_content_types.py`
- Modify: `chatgpt2applenotes/exporters/apple_notes.py:667-670`

### Step 1: Write the failing test

Add this test to `tests/test_apple_notes_content_types.py`:

```python
def test_renders_code_content_type_with_linebreaks(tmp_path: Path) -> None:
    """code content type preserves line breaks."""
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
                    "text": "def foo():\n    return 1",
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    # line breaks should be preserved
    assert "<br>" in html or "<br/>" in html or "<br />" in html
```

### Step 2: Run test to verify it fails

Run: `cd /Users/acolomba/src/chatgpt2applenotes/.worktrees/code-block-linebreaks && uv run pytest tests/test_apple_notes_content_types.py::test_renders_code_content_type_with_linebreaks -v`

Expected: FAIL

### Step 3: Update _render_code_content method

Replace the `_render_code_content` method (around line 667) with:

```python
    def _render_code_content(self, message: Message) -> str:
        """renders code content type as monospace block."""
        text = message.content.get("text", "")
        escaped = html_lib.escape(text)
        # converts newlines to <br> for Apple Notes
        with_breaks = escaped.replace("\n", "<br>")
        return f"<div><tt>{with_breaks}</tt></div>"
```

### Step 4: Run test to verify it passes

Run: `cd /Users/acolomba/src/chatgpt2applenotes/.worktrees/code-block-linebreaks && uv run pytest tests/test_apple_notes_content_types.py::test_renders_code_content_type_with_linebreaks -v`

Expected: PASS

### Step 5: Run all tests

Run: `cd /Users/acolomba/src/chatgpt2applenotes/.worktrees/code-block-linebreaks && uv run pytest -v`

Expected: All tests pass

### Step 6: Commit

```bash
cd /Users/acolomba/src/chatgpt2applenotes/.worktrees/code-block-linebreaks
git add tests/test_apple_notes_content_types.py chatgpt2applenotes/exporters/apple_notes.py
git commit -m "feat: preserve line breaks in code content type

Applies the same newline-to-br conversion to the code content type
renderer for consistency with fenced code blocks.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Final Verification

### Step 1: Run full test suite

Run: `cd /Users/acolomba/src/chatgpt2applenotes/.worktrees/code-block-linebreaks && uv run pytest -v`

Expected: All tests pass (79+ tests)

### Step 2: Push branch

```bash
cd /Users/acolomba/src/chatgpt2applenotes/.worktrees/code-block-linebreaks
git push -u origin feature/code-block-linebreaks
```
