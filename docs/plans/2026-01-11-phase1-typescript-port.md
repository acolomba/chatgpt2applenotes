# Phase 1: TypeScript Port & Validation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Port chatgpt-exporter TypeScript code to Python, producing byte-identical HTML output for validation.

**Architecture:** Direct line-by-line translation of TypeScript processConversation and HTML exporter, using markdown-it-py for AST parsing and custom renderer for exact HTML control. Validate against reference files using byte-for-byte comparison.

**Tech Stack:** Python 3.9+, markdown-it-py, pytest, filecmp

---

## Task 1: Project Structure Setup

**Files:**
- Create: `chatgpt2applenotes/__init__.py`
- Create: `chatgpt2applenotes/core/__init__.py`
- Create: `chatgpt2applenotes/exporters/__init__.py`
- Create: `tests/__init__.py`
- Create: `output/.gitkeep`
- Create: `references/apple-note-html.txt`

**Step 1: Create package structure**

```bash
mkdir -p chatgpt2applenotes/core chatgpt2applenotes/exporters tests output references
touch chatgpt2applenotes/__init__.py
touch chatgpt2applenotes/core/__init__.py
touch chatgpt2applenotes/exporters/__init__.py
touch tests/__init__.py
touch output/.gitkeep
```

**Step 2: Add output to gitignore**

Edit `.gitignore` and add:

```text
# output
/output/*
!/output/.gitkeep
```

**Step 3: Create placeholder for Apple Notes reference**

```bash
touch references/apple-note-html.txt
```

**Step 4: Commit**

```bash
git add .
git commit -m "feat: add project structure for chatgpt2applenotes"
```

---

## Task 2: Define Data Models

**Files:**
- Create: `chatgpt2applenotes/core/models.py`
- Create: `tests/test_models.py`
- Reference: `/Users/acolomba/src/chatgpt-exporter/src/api.ts` (TypeScript interfaces)

**Step 1: Write test for Conversation model**

Create `tests/test_models.py`:

```python
from chatgpt2applenotes.core.models import Conversation, Message, Author


def test_conversation_creation():
    conv = Conversation(
        id="conv-123",
        title="Test Conversation",
        create_time=1234567890.0,
        update_time=1234567890.0,
        messages=[]
    )
    assert conv.id == "conv-123"
    assert conv.title == "Test Conversation"
    assert len(conv.messages) == 0


def test_message_creation():
    msg = Message(
        id="msg-123",
        author=Author(role="user", name=None, metadata={}),
        create_time=1234567890.0,
        content={"content_type": "text", "parts": ["Hello"]},
        metadata={}
    )
    assert msg.id == "msg-123"
    assert msg.author.role == "user"
    assert msg.content["parts"][0] == "Hello"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`

Expected: FAIL with "No module named 'chatgpt2applenotes.core.models'"

**Step 3: Implement data models**

Create `chatgpt2applenotes/core/models.py`:

```python
"""Data models for ChatGPT conversations (ported from TypeScript)."""
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Author:
    """Message author information."""
    role: str  # "user", "assistant", "system"
    name: Optional[str] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MessageContent:
    """Message content structure."""
    content_type: str
    parts: list[str]


@dataclass
class Message:
    """Individual message in a conversation."""
    id: str
    author: Author
    create_time: float
    content: dict[str, Any]  # Flexible for various content types
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Conversation:
    """Complete conversation structure."""
    id: str
    title: str
    create_time: float
    update_time: float
    messages: list[Message]
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`

Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add chatgpt2applenotes/core/models.py tests/test_models.py
git commit -m "feat: add data models for conversations"
```

---

## Task 3: Port processConversation Parser (Part 1: Basic Structure)

**Files:**
- Create: `chatgpt2applenotes/core/parser.py`
- Create: `tests/test_parser.py`
- Reference: `/Users/acolomba/src/chatgpt-exporter/src/api.ts` (processConversation function)
- Reference: `/Users/acolomba/Downloads/chatgpt-export-json/ChatGPT-Freezing_Rye_Bread.json`

**Step 1: Write test for basic JSON parsing**

Create `tests/test_parser.py`:

```python
import json
from pathlib import Path
from chatgpt2applenotes.core.parser import process_conversation


def test_process_conversation_basic():
    """Test basic conversation processing with minimal JSON."""
    json_data = {
        "id": "conv-123",
        "title": "Test",
        "create_time": 1234567890.0,
        "update_time": 1234567890.0,
        "mapping": {
            "msg-1": {
                "id": "msg-1",
                "message": {
                    "id": "msg-1",
                    "author": {"role": "user"},
                    "create_time": 1234567890.0,
                    "content": {"content_type": "text", "parts": ["Hello"]}
                }
            }
        }
    }

    conversation = process_conversation(json_data)

    assert conversation.id == "conv-123"
    assert conversation.title == "Test"
    assert len(conversation.messages) == 1
    assert conversation.messages[0].content["parts"][0] == "Hello"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_parser.py::test_process_conversation_basic -v`

Expected: FAIL with "cannot import name 'process_conversation'"

**Step 3: Implement basic parser structure**

Create `chatgpt2applenotes/core/parser.py`:

```python
"""Parser for ChatGPT OpenAPI JSON format (ported from TypeScript)."""
from typing import Any
from chatgpt2applenotes.core.models import Conversation, Message, Author


def process_conversation(json_data: dict[str, Any]) -> Conversation:
    """
    Process a ChatGPT conversation from OpenAPI JSON format.

    Direct port of processConversation from chatgpt-exporter/src/api.ts

    Args:
        json_data: Raw conversation JSON from OpenAPI

    Returns:
        Processed Conversation object
    """
    # Extract basic conversation metadata
    conversation_id = json_data.get("id", "")
    title = json_data.get("title", "Untitled")
    create_time = json_data.get("create_time", 0.0)
    update_time = json_data.get("update_time", 0.0)

    # Process messages from mapping
    messages = _extract_messages(json_data.get("mapping", {}))

    return Conversation(
        id=conversation_id,
        title=title,
        create_time=create_time,
        update_time=update_time,
        messages=messages
    )


def _extract_messages(mapping: dict[str, Any]) -> list[Message]:
    """Extract and order messages from conversation mapping."""
    messages = []

    for node_id, node in mapping.items():
        message_data = node.get("message")
        if not message_data:
            continue

        # Skip messages without content
        content = message_data.get("content")
        if not content:
            continue

        author_data = message_data.get("author", {})
        author = Author(
            role=author_data.get("role", "unknown"),
            name=author_data.get("name"),
            metadata=author_data.get("metadata", {})
        )

        message = Message(
            id=message_data.get("id", node_id),
            author=author,
            create_time=message_data.get("create_time", 0.0),
            content=content,
            metadata=message_data.get("metadata", {})
        )

        messages.append(message)

    # Sort by create_time (TypeScript sorts by default)
    messages.sort(key=lambda m: m.create_time)

    return messages
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_parser.py::test_process_conversation_basic -v`

Expected: PASS

**Step 5: Commit**

```bash
git add chatgpt2applenotes/core/parser.py tests/test_parser.py
git commit -m "feat: add basic conversation parser"
```

---

## Task 4: Test Parser with Real Data

**Files:**
- Modify: `tests/test_parser.py`
- Reference: `/Users/acolomba/Downloads/chatgpt-export-json/ChatGPT-Freezing_Rye_Bread.json`

**Step 1: Write test with real conversation file**

Add to `tests/test_parser.py`:

```python
def test_process_real_conversation():
    """Test with actual ChatGPT export file."""
    json_path = Path("/Users/acolomba/Downloads/chatgpt-export-json/ChatGPT-Freezing_Rye_Bread.json")

    with open(json_path) as f:
        json_data = json.load(f)

    conversation = process_conversation(json_data)

    # Basic validations
    assert conversation.id
    assert conversation.title == "Freezing Rye Bread"
    assert len(conversation.messages) > 0

    # Verify message structure
    for msg in conversation.messages:
        assert msg.id
        assert msg.author.role in ["user", "assistant", "system"]
        assert msg.create_time > 0
```

**Step 2: Run test to verify behavior**

Run: `pytest tests/test_parser.py::test_process_real_conversation -v`

Expected: May PASS or FAIL depending on actual data structure - iterate on parser if needed

**Step 3: Fix any issues found**

If test fails, debug and fix `parser.py` to handle edge cases in real data.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_parser.py -v`

Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add tests/test_parser.py chatgpt2applenotes/core/parser.py
git commit -m "test: add real conversation parsing test"
```

---

## Task 5: Add Markdown Renderer Foundation

**Files:**
- Create: `chatgpt2applenotes/core/markdown_ast.py`
- Create: `tests/test_markdown.py`
- Modify: `pyproject.toml`

**Step 1: Add markdown-it-py dependency**

Edit `pyproject.toml` dependencies:

```toml
dependencies = [
    "markdown-it-py~=3.0",
]
```

Install: `pip install -e ".[dev]"`

**Step 2: Write test for markdown rendering**

Create `tests/test_markdown.py`:

```python
from chatgpt2applenotes.core.markdown_ast import render_markdown_to_html


def test_render_simple_text():
    markdown = "Hello world"
    html = render_markdown_to_html(markdown)
    assert html == "<p>Hello world</p>"


def test_render_bold():
    markdown = "**bold text**"
    html = render_markdown_to_html(markdown)
    assert html == "<p><strong>bold text</strong></p>"


def test_render_code_block():
    markdown = "```python\nprint('hello')\n```"
    html = render_markdown_to_html(markdown)
    assert '<code class="language-python">' in html
    assert "print('hello')" in html
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/test_markdown.py -v`

Expected: FAIL with "cannot import name 'render_markdown_to_html'"

**Step 4: Implement markdown renderer**

Create `chatgpt2applenotes/core/markdown_ast.py`:

```python
"""Markdown to HTML renderer with full control over output format."""
from markdown_it import MarkdownIt


def render_markdown_to_html(markdown: str) -> str:
    """
    Render markdown to HTML matching chatgpt-exporter output.

    Uses markdown-it-py for parsing to AST, with custom rendering
    to match exact HTML output from TypeScript implementation.

    Args:
        markdown: Input markdown text

    Returns:
        HTML string matching reference output
    """
    md = MarkdownIt()
    tokens = md.parse(markdown)

    # For now, use default renderer - we'll customize later
    html = md.render(markdown)

    # Strip trailing newline for consistency
    return html.rstrip('\n')
```

**Step 5: Run test to verify basic functionality**

Run: `pytest tests/test_markdown.py -v`

Expected: May partially pass - we'll refine in next task

**Step 6: Commit**

```bash
git add chatgpt2applenotes/core/markdown_ast.py tests/test_markdown.py pyproject.toml
git commit -m "feat: add markdown renderer foundation"
```

---

## Task 6: Create HTML Exporter Foundation

**Files:**
- Create: `chatgpt2applenotes/exporters/base.py`
- Create: `chatgpt2applenotes/exporters/html.py`
- Create: `tests/test_html_exporter.py`

**Step 1: Write test for HTML exporter interface**

Create `tests/test_html_exporter.py`:

```python
from pathlib import Path
from chatgpt2applenotes.core.models import Conversation, Message, Author
from chatgpt2applenotes.exporters.html import HTMLExporter


def test_html_exporter_basic():
    """Test basic HTML export."""
    conversation = Conversation(
        id="conv-123",
        title="Test Conversation",
        create_time=1234567890.0,
        update_time=1234567890.0,
        messages=[
            Message(
                id="msg-1",
                author=Author(role="user"),
                create_time=1234567890.0,
                content={"content_type": "text", "parts": ["Hello"]},
            )
        ]
    )

    exporter = HTMLExporter()
    output_dir = Path("output/test")
    output_dir.mkdir(parents=True, exist_ok=True)

    exporter.export(conversation, str(output_dir), dry_run=False, overwrite=True)

    output_file = output_dir / "ChatGPT-Test_Conversation.html"
    assert output_file.exists()

    html = output_file.read_text()
    assert "<!DOCTYPE html>" in html
    assert "Test Conversation" in html
    assert "Hello" in html
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_html_exporter.py -v`

Expected: FAIL with import errors

**Step 3: Implement base exporter**

Create `chatgpt2applenotes/exporters/base.py`:

```python
"""Base exporter interface."""
from abc import ABC, abstractmethod
from chatgpt2applenotes.core.models import Conversation


class Exporter(ABC):
    """Abstract base class for conversation exporters."""

    @abstractmethod
    def export(
        self,
        conversation: Conversation,
        destination: str,
        dry_run: bool = False,
        overwrite: bool = False
    ) -> None:
        """
        Export a conversation to the destination.

        Args:
            conversation: The conversation to export
            destination: Where to write the export (interpretation varies by exporter)
            dry_run: If True, don't actually write anything
            overwrite: If True, overwrite existing content
        """
        pass
```

**Step 4: Implement HTML exporter**

Create `chatgpt2applenotes/exporters/html.py`:

```python
"""HTML exporter matching chatgpt-exporter output."""
import html as html_lib
from pathlib import Path
from chatgpt2applenotes.core.models import Conversation
from chatgpt2applenotes.exporters.base import Exporter


class HTMLExporter(Exporter):
    """Export conversations to HTML format (matching TypeScript implementation)."""

    def export(
        self,
        conversation: Conversation,
        destination: str,
        dry_run: bool = False,
        overwrite: bool = False
    ) -> None:
        """Export conversation to HTML file."""
        # Generate filename from title
        safe_title = conversation.title.replace(' ', '_').replace('/', '-')
        filename = f"ChatGPT-{safe_title}.html"
        output_path = Path(destination) / filename

        if dry_run:
            print(f"Would write to: {output_path}")
            return

        if output_path.exists() and not overwrite:
            print(f"Skipping existing file: {output_path}")
            return

        # Generate HTML
        html_content = self._generate_html(conversation)

        # Write to file
        output_path.write_text(html_content, encoding='utf-8')

    def _generate_html(self, conversation: Conversation) -> str:
        """Generate HTML content for conversation."""
        # Basic HTML structure - will refine to match reference
        title_escaped = html_lib.escape(conversation.title)

        messages_html = []
        for msg in conversation.messages:
            author_label = msg.author.role.capitalize()
            parts = msg.content.get("parts", [])
            content_text = " ".join(str(p) for p in parts if p)
            content_escaped = html_lib.escape(content_text)

            messages_html.append(f'''
                <div class="message">
                    <div class="author">{author_label}</div>
                    <div class="content"><p>{content_escaped}</p></div>
                </div>
            ''')

        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title_escaped}</title>
</head>
<body>
    <h1>{title_escaped}</h1>
    {"".join(messages_html)}
</body>
</html>'''

        return html
```

**Step 5: Run test to verify basic functionality**

Run: `pytest tests/test_html_exporter.py -v`

Expected: PASS

**Step 6: Commit**

```bash
git add chatgpt2applenotes/exporters/ tests/test_html_exporter.py
git commit -m "feat: add HTML exporter foundation"
```

---

## Task 7: Create Validation Script

**Files:**
- Create: `validate.py`
- Create: `tests/test_validation.py`

**Step 1: Write validation script**

Create `validate.py`:

```python
#!/usr/bin/env python3
"""Validation script to compare generated HTML with reference."""
import filecmp
import json
import sys
from pathlib import Path
from chatgpt2applenotes.core.parser import process_conversation
from chatgpt2applenotes.exporters.html import HTMLExporter


def validate_file(json_path: Path, reference_html: Path, output_dir: Path) -> tuple[bool, str]:
    """
    Validate single file against reference.

    Returns:
        (success, message) tuple
    """
    try:
        # Parse JSON
        with open(json_path) as f:
            json_data = json.load(f)

        conversation = process_conversation(json_data)

        # Export to output directory
        exporter = HTMLExporter()
        exporter.export(conversation, str(output_dir), dry_run=False, overwrite=True)

        # Determine output filename
        safe_title = conversation.title.replace(' ', '_').replace('/', '-')
        output_file = output_dir / f"ChatGPT-{safe_title}.html"

        # Compare files
        if not output_file.exists():
            return False, f"Output file not created: {output_file}"

        if not reference_html.exists():
            return False, f"Reference file not found: {reference_html}"

        if filecmp.cmp(output_file, reference_html, shallow=False):
            return True, "✓ Files match exactly"
        else:
            return False, "✗ Files differ"

    except Exception as e:
        return False, f"Error: {e}"


def main():
    """Run validation on sample files."""
    sample_files = [
        "ChatGPT-Freezing_Rye_Bread",
        "ChatGPT-Fix_libflac_error",
        "ChatGPT-Authentication_session_explained",
        "ChatGPT-Best_Non-Alcoholic_Beer",
        "ChatGPT-Wegovy_and_Glucose_Stabilization",
    ]

    json_dir = Path("/Users/acolomba/Downloads/chatgpt-export-json")
    reference_dir = Path("/Users/acolomba/Downloads/chatgpt-export-html")
    output_dir = Path("output/html")
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []

    for basename in sample_files:
        json_path = json_dir / f"{basename}.json"
        reference_html = reference_dir / f"{basename}.html"

        print(f"\nValidating {basename}...")
        success, message = validate_file(json_path, reference_html, output_dir)
        results.append((basename, success, message))
        print(f"  {message}")

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    for basename, success, message in results:
        print(f"{basename}: {message}")

    print(f"\n{passed}/{total} files match exactly")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
```

**Step 2: Make script executable**

```bash
chmod +x validate.py
```

**Step 3: Run validation (expected to fail)**

Run: `python validate.py`

Expected: Most/all files will differ - this establishes baseline

**Step 4: Commit**

```bash
git add validate.py
git commit -m "feat: add validation script for HTML output"
```

---

## Task 8: Analyze Reference HTML Structure

**Files:**
- Create: `docs/reference-html-analysis.md`

**Step 1: Examine reference HTML files**

```bash
head -50 /Users/acolomba/Downloads/chatgpt-export-html/ChatGPT-Freezing_Rye_Bread.html > docs/reference-html-analysis.md
```

**Step 2: Document structure**

Edit `docs/reference-html-analysis.md` and add analysis:

```markdown
# Reference HTML Structure Analysis

## DOCTYPE and Head

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>[Conversation Title]</title>
    <style>
        /* CSS from chatgpt-exporter */
    </style>
</head>
```

## Message Structure

[Document the exact structure of messages, code blocks, etc.]

## Key Differences from Current Implementation

1. CSS styling in <style> tag
2. Message HTML structure
3. Code block formatting
4. Markdown rendering details

```

**Step 3: Commit analysis**

```bash
git add docs/reference-html-analysis.md
git commit -m "docs: analyze reference HTML structure"
```

---

## Task 9: Match HTML Template Structure

**Files:**
- Modify: `chatgpt2applenotes/exporters/html.py`
- Reference: `/Users/acolomba/src/chatgpt-exporter/src/exporter/html.ts`

**Step 1: Extract exact HTML template from TypeScript**

Read `/Users/acolomba/src/chatgpt-exporter/src/exporter/html.ts` and port the exact HTML template structure.

**Step 2: Update HTMLExporter._generate_html()**

Modify to match reference structure exactly, including:
- DOCTYPE
- meta tags
- CSS styles (port from TypeScript)
- Message wrapper structure
- Author labels
- Content formatting

**Step 3: Run validation**

Run: `python validate.py`

Expected: Closer match, but likely still differences in markdown rendering

**Step 4: Commit**

```bash
git add chatgpt2applenotes/exporters/html.py
git commit -m "feat: match HTML template structure to reference"
```

---

## Task 10: Refine Markdown Rendering (Iterative)

**Files:**
- Modify: `chatgpt2applenotes/core/markdown_ast.py`
- Modify: `tests/test_markdown.py`

**Step 1: Compare markdown output with reference**

Extract markdown content from reference HTML and generated HTML, identify differences.

**Step 2: Implement custom renderer**

Create custom renderer class to control:
- Paragraph tags and whitespace
- Bold/italic formatting
- Code blocks with language tags
- Lists and nesting
- Links

**Step 3: Run validation**

Run: `python validate.py`

Expected: Progressively closer matches

**Step 4: Iterate**

Repeat steps 1-3 until validation passes for sample files.

**Step 5: Commit each iteration**

```bash
git add chatgpt2applenotes/core/markdown_ast.py tests/test_markdown.py
git commit -m "feat: refine markdown rendering - [specific improvement]"
```

---

## Task 11: Handle Edge Cases from Real Data

**Files:**
- Modify: `chatgpt2applenotes/core/parser.py`
- Modify: `tests/test_parser.py`

**Step 1: Identify edge cases**

Run validation and examine failures. Common issues:
- Messages with null content
- Code blocks with special characters
- Nested message structures
- Different content types (images, etc.)

**Step 2: Add tests for edge cases**

Add specific tests to `tests/test_parser.py` for each edge case found.

**Step 3: Fix parser to handle edge cases**

Update `parser.py` to handle each case.

**Step 4: Run validation**

Run: `python validate.py`

Expected: All 5 sample files pass

**Step 5: Commit**

```bash
git add chatgpt2applenotes/core/parser.py tests/test_parser.py
git commit -m "fix: handle edge cases in conversation parsing"
```

---

## Task 12: Full Validation Suite

**Files:**
- Modify: `validate.py`
- Create: `docs/validation-report.md`

**Step 1: Extend validation to all files**

Modify `validate.py` to process all JSON files in the export directory (not just the 5 samples).

**Step 2: Run full validation**

Run: `python validate.py > docs/validation-report.md`

Expected: All files should match if sample validation passed

**Step 3: Fix any remaining issues**

If failures occur, debug and fix.

**Step 4: Commit**

```bash
git add validate.py docs/validation-report.md chatgpt2applenotes/
git commit -m "feat: complete Phase 1 - byte-identical HTML validation"
```

---

## Success Criteria

- [ ] All 5 sample files produce byte-identical HTML
- [ ] All JSON files in export directory produce byte-identical HTML
- [ ] Tests pass: `pytest tests/ -v`
- [ ] Validation passes: `python validate.py`

## Next Phase

Once Phase 1 is complete:
- Phase 2: CLI & File Handling
- Phase 3: Apple Notes Integration

Use @superpowers:writing-plans to create implementation plans for subsequent phases.
