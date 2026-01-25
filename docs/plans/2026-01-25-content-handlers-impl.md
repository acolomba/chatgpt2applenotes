# Modular Content Handlers Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor html_renderer.py into modular handlers per content type with Flask-style decorators.

**Architecture:** Handler registry with `@handler("content_type")` decorators, nested `@part_handler()` for multimodal parts, separate utility modules, `--render-internals` CLI flag.

**Tech Stack:** Python 3.11+, markdown-it-py, pytest

---

## Task Dependencies

```text
Task 1 (utils/latex)     ─┬─► Task 5 (utils/markdown) ─┬─► Task 8 (text handler)
Task 2 (utils/spacing)   ─┤                            │
Task 3 (utils/citations) ─┘                            ├─► Task 9 (multimodal handler)
                                                       │
Task 4 (registry)        ──────────────────────────────┼─► Task 10 (code handler)
                                                       ├─► Task 11 (execution handler)
Task 6 (part registry)   ─► Task 7 (audio parts)  ────►├─► Task 12 (browsing handler)
                                                       ├─► Task 13 (internals handler)
                                                       ├─► Task 14 (errors handler)
                                                       └─► Task 15 (app_context handler)

Task 16 (renderer integration) ◄── Tasks 8-15

Task 17 (CLI flag) ◄── Task 16

Task 18 (integration tests) ◄── Task 17
```

**Parallelizable groups:**

- Group A (no deps): Tasks 1, 2, 3, 4, 6
- Group B (after Group A): Tasks 5, 7
- Group C (after 4, 5): Tasks 8, 10, 11, 12, 13, 14, 15
- Group D (after 6, 7, 5): Task 9
- Group E (after all handlers): Task 16
- Group F (after 16): Tasks 17, 18

---

## Task 1: Create utils/latex module

**Files:**

- Create: `chatgpt2applenotes/exporters/handlers/utils/init.py`
- Create: `chatgpt2applenotes/exporters/handlers/utils/latex.py`
- Create: `tests/exporters/handlers/utils/init.py`
- Create: `tests/exporters/handlers/utils/test_latex.py`

### Step 1: Create directory structure

```bash
mkdir -p chatgpt2applenotes/exporters/handlers/utils
mkdir -p tests/exporters/handlers/utils
touch chatgpt2applenotes/exporters/handlers/utils/init.py
touch tests/exporters/handlers/utils/init.py
```

### Step 2: Write the failing test

```python
# tests/exporters/handlers/utils/test_latex.py
"""tests for LaTeX protection utilities."""

import pytest

from chatgpt2applenotes.exporters.handlers.utils.latex import (
    protect_latex,
    restore_latex,
)


def test_protect_latex_inline():
    """protects inline LaTeX $...$ from markdown processing."""
    text = "The formula $E=mc^2$ is famous"
    protected, matches = protect_latex(text)
    assert "$E=mc^2$" not in protected
    assert len(matches) == 1
    assert matches[0] == "$E=mc^2$"


def test_protect_latex_display():
    """protects display LaTeX $$...$$ from markdown processing."""
    text = "Display: $$\\int_0^1 x^2 dx$$"
    protected, matches = protect_latex(text)
    assert "$$" not in protected
    assert len(matches) == 1


def test_protect_latex_brackets():
    """protects \\[...\\] and \\(...\\) LaTeX from markdown processing."""
    text = "Inline \\(a+b\\) and display \\[x^2\\]"
    protected, matches = protect_latex(text)
    assert "\\(" not in protected
    assert "\\[" not in protected
    assert len(matches) == 2


def test_restore_latex():
    """restores LaTeX from placeholders with HTML escaping."""
    text = "The formula \u25631\u2563 is famous"
    matches = ["$E=mc^2$"]
    # note: index in placeholder is 0-based in actual implementation
    text_with_placeholder = "The formula \u25630\u2563 is famous"
    restored = restore_latex(text_with_placeholder, matches)
    assert "$E=mc^2$" in restored


def test_protect_and_restore_roundtrip():
    """protects and restores LaTeX correctly."""
    original = "Variables $a_1$ and $b_2$ are defined."
    protected, matches = protect_latex(original)
    restored = restore_latex(protected, matches)
    assert "$a_1$" in restored
    assert "$b_2$" in restored


def test_no_latex_returns_empty_matches():
    """text without LaTeX returns empty matches list."""
    text = "No math here"
    protected, matches = protect_latex(text)
    assert protected == text
    assert matches == []
```

### Step 3: Run test to verify it fails

Run: `pytest tests/exporters/handlers/utils/test_latex.py -v`
Expected: FAIL with ModuleNotFoundError

### Step 4: Write implementation

```python
# chatgpt2applenotes/exporters/handlers/utils/latex.py
"""LaTeX protection utilities for markdown processing."""

import html
import re

LATEX_PATTERN = re.compile(
    r"(\$\$[\s\S]+?\$\$)|(\$[^\$\n]+?\$)|(\\\[[\s\S]+?\\\])|(\\\([\s\S]+?\\\))",
    re.MULTILINE,
)


def protect_latex(text: str) -> tuple[str, list[str]]:
    """
    replaces LaTeX with placeholders to protect from markdown processing.

    Args:
        text: input text containing LaTeX

    Returns:
        tuple of (protected text, list of LaTeX matches)
    """
    matches: list[str] = []

    def replacer(match: re.Match[str]) -> str:
        matches.append(match.group(0))
        return f"\u2563{len(matches) - 1}\u2563"

    return LATEX_PATTERN.sub(replacer, text), matches


def restore_latex(text: str, matches: list[str]) -> str:
    """
    restores LaTeX from placeholders with HTML escaping.

    Args:
        text: text with placeholders
        matches: list of original LaTeX strings

    Returns:
        text with LaTeX restored (HTML-escaped)
    """
    for i, latex in enumerate(matches):
        text = text.replace(f"\u2563{i}\u2563", html.escape(latex))
    return text
```

### Step 5: Run test to verify it passes

Run: `pytest tests/exporters/handlers/utils/test_latex.py -v`
Expected: PASS

### Step 6: Commit

```bash
git add chatgpt2applenotes/exporters/handlers/utils/ tests/exporters/handlers/utils/
git commit -m "feat(handlers): add latex protection utilities"
```

---

## Task 2: Create utils/spacing module

**Files:**

- Create: `chatgpt2applenotes/exporters/handlers/utils/spacing.py`
- Create: `tests/exporters/handlers/utils/test_spacing.py`

### Step 1: Write the failing test

```python
# tests/exporters/handlers/utils/test_spacing.py
"""tests for block spacing utilities."""

from chatgpt2applenotes.exporters.handlers.utils.spacing import add_block_spacing


def test_adds_spacing_between_divs():
    """adds spacing between adjacent div elements."""
    html = "</div><div>"
    result = add_block_spacing(html)
    assert "<div><br></div>" in result


def test_adds_spacing_between_different_blocks():
    """adds spacing between different block elements."""
    html = "</ul><div>"
    result = add_block_spacing(html)
    assert "<div><br></div>" in result


def test_handles_consecutive_blocks():
    """handles multiple consecutive block elements."""
    html = "</div><div></div><div>"
    result = add_block_spacing(html)
    assert result.count("<div><br></div>") == 2


def test_cleans_empty_divs_in_lists():
    """removes empty divs from loose list rendering."""
    html = "<li><div></div>content</li>"
    result = add_block_spacing(html)
    assert "<li>\ncontent</li>" in result


def test_no_change_for_inline_content():
    """does not modify inline content."""
    html = "<span>hello</span><span>world</span>"
    result = add_block_spacing(html)
    assert result == html
```

### Step 2: Run test to verify it fails

Run: `pytest tests/exporters/handlers/utils/test_spacing.py -v`
Expected: FAIL with ModuleNotFoundError

### Step 3: Write implementation

```python
# chatgpt2applenotes/exporters/handlers/utils/spacing.py
"""block spacing utilities for Apple Notes HTML."""

import re


def add_block_spacing(html: str) -> str:
    """
    adds <div><br></div> between adjacent block elements at top level.

    Args:
        html: input HTML

    Returns:
        HTML with spacing added between block elements
    """
    # cleans up empty divs from markdown-it's loose list rendering
    html = re.sub(
        r"(<(?:li|blockquote)[^>]*>)\s*<div>(?:<br\s*/?>|\s)*</div>\s*",
        r"\1\n",
        html,
        flags=re.IGNORECASE,
    )

    # uses a unique marker to prevent infinite loops
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

    # repeatedly applies until no more changes (handles consecutive blocks)
    prev = ""
    while prev != html:
        prev = html
        html = block_pattern.sub(add_spacer, html)

    # replaces markers with actual spacers
    return html.replace(spacer_marker, "<div><br></div>")
```

### Step 4: Run test to verify it passes

Run: `pytest tests/exporters/handlers/utils/test_spacing.py -v`
Expected: PASS

### Step 5: Commit

```bash
git add chatgpt2applenotes/exporters/handlers/utils/spacing.py tests/exporters/handlers/utils/test_spacing.py
git commit -m "feat(handlers): add block spacing utilities"
```

---

## Task 3: Create utils/citations module

**Files:**

- Create: `chatgpt2applenotes/exporters/handlers/utils/citations.py`
- Create: `tests/exporters/handlers/utils/test_citations.py`

### Step 1: Write the failing test

```python
# tests/exporters/handlers/utils/test_citations.py
"""tests for citation rendering utilities."""

from chatgpt2applenotes.exporters.handlers.utils.citations import render_citations


def test_replaces_citation_with_link():
    """replaces citation marker with attribution link."""
    html = "See the guide. \ue200cite\ue202turn0search3\ue201"
    metadata = {
        "content_references": [
            {
                "matched_text": "\ue200cite\ue202turn0search3\ue201",
                "items": [{"url": "https://example.com", "attribution": "Example"}],
            }
        ]
    }
    result = render_citations(html, metadata)
    assert '<a href="https://example.com">Example</a>' in result
    assert "\ue200" not in result


def test_renders_multiple_sources():
    """renders multiple sources as comma-separated links."""
    html = "Info \ue200cite\ue202turn0\ue201"
    metadata = {
        "content_references": [
            {
                "matched_text": "\ue200cite\ue202turn0\ue201",
                "items": [
                    {
                        "url": "https://a.com",
                        "attribution": "A",
                        "supporting_websites": [
                            {"url": "https://b.com", "attribution": "B"}
                        ],
                    }
                ],
            }
        ]
    }
    result = render_citations(html, metadata)
    assert "A</a>, <a" in result
    assert "B</a>" in result


def test_removes_marker_without_items():
    """removes citation marker when no items present."""
    html = "No source. \ue200cite\ue202turn0\ue201"
    metadata = {
        "content_references": [
            {"matched_text": "\ue200cite\ue202turn0\ue201", "items": []}
        ]
    }
    result = render_citations(html, metadata)
    assert "No source." in result
    assert "\ue200" not in result
    assert "<a href" not in result


def test_skips_whitespace_markers():
    """skips whitespace-only matched_text to preserve spaces."""
    html = "Hello world"
    metadata = {"content_references": [{"matched_text": " ", "items": []}]}
    result = render_citations(html, metadata)
    assert result == "Hello world"


def test_no_metadata_returns_unchanged():
    """returns unchanged HTML when no metadata."""
    html = "<div>content</div>"
    result = render_citations(html, None)
    assert result == html
```

### Step 2: Run test to verify it fails

Run: `pytest tests/exporters/handlers/utils/test_citations.py -v`
Expected: FAIL with ModuleNotFoundError

### Step 3: Write implementation

```python
# chatgpt2applenotes/exporters/handlers/utils/citations.py
"""citation rendering utilities for ChatGPT content references."""

import html
from typing import Any


def render_citations(text: str, metadata: dict[str, Any] | None) -> str:
    """
    replaces citation markers with attribution links.

    Args:
        text: HTML text with citation markers
        metadata: message metadata containing content_references

    Returns:
        text with citations replaced by links
    """
    if not metadata:
        return text

    content_refs = metadata.get("content_references", [])
    if not content_refs:
        return text

    for ref in content_refs:
        matched_text = ref.get("matched_text", "")
        # skips empty or whitespace-only markers
        if not matched_text or matched_text.isspace():
            continue

        items = ref.get("items", [])
        if not items:
            # no items, just remove the marker
            text = text.replace(matched_text, "")
            continue

        # builds links from items and supporting_websites
        links = []
        for item in items:
            url = item.get("url", "")
            attribution = item.get("attribution", "")
            if url and attribution:
                escaped_url = html.escape(url)
                escaped_attr = html.escape(attribution)
                links.append(f'<a href="{escaped_url}">{escaped_attr}</a>')

            # adds supporting websites
            for support in item.get("supporting_websites", []):
                s_url = support.get("url", "")
                s_attr = support.get("attribution", "")
                if s_url and s_attr:
                    escaped_url = html.escape(s_url)
                    escaped_attr = html.escape(s_attr)
                    links.append(f'<a href="{escaped_url}">{escaped_attr}</a>')

        if links:
            replacement = "(" + ", ".join(links) + ")"
            text = text.replace(matched_text, replacement)
        else:
            text = text.replace(matched_text, "")

    return text
```

### Step 4: Run test to verify it passes

Run: `pytest tests/exporters/handlers/utils/test_citations.py -v`
Expected: PASS

### Step 5: Commit

```bash
git add chatgpt2applenotes/exporters/handlers/utils/citations.py tests/exporters/handlers/utils/test_citations.py
git commit -m "feat(handlers): add citation rendering utilities"
```

---

## Task 4: Create handler registry

**Files:**

- Create: `chatgpt2applenotes/exporters/handlers/init.py`
- Create: `tests/exporters/handlers/init.py`
- Create: `tests/exporters/handlers/test_registry.py`

### Step 1: Write the failing test

```python
# tests/exporters/handlers/test_registry.py
"""tests for handler registry."""

import pytest

from chatgpt2applenotes.exporters.handlers import (
    HandlerRegistry,
    RenderContext,
    handler,
)


def test_render_context_defaults():
    """RenderContext has correct defaults."""
    ctx = RenderContext()
    assert ctx.render_internals is False


def test_handler_decorator_registers_class():
    """@handler decorator registers handler class."""
    registry = HandlerRegistry()

    @handler("test_type", registry=registry)
    class TestHandler:
        def render(self, content, metadata, ctx):
            return "<div>test</div>"

    assert "test_type" in registry._handlers


def test_handler_decorator_with_multiple_types():
    """@handler decorator registers multiple content types."""
    registry = HandlerRegistry()

    @handler(["type_a", "type_b"], registry=registry)
    class MultiHandler:
        def render(self, content, metadata, ctx):
            return "<div>multi</div>"

    assert "type_a" in registry._handlers
    assert "type_b" in registry._handlers


def test_registry_render_dispatches_to_handler():
    """registry.render dispatches to correct handler."""
    registry = HandlerRegistry()

    @handler("text", registry=registry)
    class TextHandler:
        def render(self, content, metadata, ctx):
            return f"<div>{content.get('value')}</div>"

    ctx = RenderContext()
    result = registry.render({"content_type": "text", "value": "hello"}, None, ctx)
    assert result == "<div>hello</div>"


def test_registry_returns_none_for_unknown_type():
    """registry.render returns None for unknown content type."""
    registry = HandlerRegistry()
    ctx = RenderContext()
    result = registry.render({"content_type": "unknown"}, None, ctx)
    assert result is None


def test_internal_handler_skipped_without_flag():
    """internal handler is skipped when render_internals=False."""
    registry = HandlerRegistry()

    @handler("thoughts", internal=True, registry=registry)
    class ThoughtsHandler:
        def render(self, content, metadata, ctx):
            return "<div>thoughts</div>"

    ctx = RenderContext(render_internals=False)
    result = registry.render({"content_type": "thoughts"}, None, ctx)
    assert result is None


def test_internal_handler_rendered_with_flag():
    """internal handler renders when render_internals=True."""
    registry = HandlerRegistry()

    @handler("thoughts", internal=True, registry=registry)
    class ThoughtsHandler:
        def render(self, content, metadata, ctx):
            return "<div>thoughts</div>"

    ctx = RenderContext(render_internals=True)
    result = registry.render({"content_type": "thoughts"}, None, ctx)
    assert result == "<div>thoughts</div>"
```

### Step 2: Run test to verify it fails

Run: `pytest tests/exporters/handlers/test_registry.py -v`
Expected: FAIL with ModuleNotFoundError

### Step 3: Write implementation

```python
# chatgpt2applenotes/exporters/handlers/init.py
"""handler registry and base types for content rendering."""

from dataclasses import dataclass
from typing import Any, Optional, Protocol, TypeVar


@dataclass
class RenderContext:
    """context passed to handlers during rendering."""

    render_internals: bool = False


class ContentHandler(Protocol):
    """protocol for content handlers."""

    content_type: str | list[str]
    internal: bool

    def render(
        self, content: dict[str, Any], metadata: dict[str, Any] | None, ctx: RenderContext
    ) -> str: ...


class HandlerRegistry:
    """registry for content handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, ContentHandler] = {}

    def register(self, handler_instance: ContentHandler) -> None:
        """registers a handler for its content type(s)."""
        types = (
            handler_instance.content_type
            if isinstance(handler_instance.content_type, list)
            else [handler_instance.content_type]
        )
        for t in types:
            self._handlers[t] = handler_instance

    def render(
        self,
        content: dict[str, Any],
        metadata: dict[str, Any] | None,
        ctx: RenderContext,
    ) -> str | None:
        """
        renders content using the appropriate handler.

        Args:
            content: content dict with content_type key
            metadata: optional message metadata
            ctx: render context with flags

        Returns:
            rendered HTML string, or None if unhandled/skipped
        """
        content_type = content.get("content_type", "text")
        handler_instance = self._handlers.get(content_type)

        if not handler_instance:
            return None

        if handler_instance.internal and not ctx.render_internals:
            return None

        return handler_instance.render(content, metadata, ctx)


# global registry
registry = HandlerRegistry()

T = TypeVar("T")


def handler(
    content_type: str | list[str],
    internal: bool = False,
    registry: HandlerRegistry = registry,
):
    """
    decorator to register a content handler.

    Args:
        content_type: content type string or list of strings
        internal: if True, only render when render_internals=True
        registry: registry to register with (defaults to global)

    Returns:
        decorator function
    """

    def decorator(cls: type[T]) -> type[T]:
        cls.content_type = content_type  # type: ignore[attr-defined]
        cls.internal = internal  # type: ignore[attr-defined]
        registry.register(cls())  # type: ignore[arg-type]
        return cls

    return decorator
```

### Step 4: Run test to verify it passes

Run: `pytest tests/exporters/handlers/test_registry.py -v`
Expected: PASS

### Step 5: Commit

```bash
mkdir -p tests/exporters/handlers
touch tests/exporters/handlers/init.py
git add chatgpt2applenotes/exporters/handlers/init.py tests/exporters/handlers/
git commit -m "feat(handlers): add handler registry with Flask-style decorator"
```

---

## Task 5: Create utils/markdown module

**Depends on:** Tasks 1, 2

**Files:**

- Create: `chatgpt2applenotes/exporters/handlers/utils/markdown.py`
- Create: `tests/exporters/handlers/utils/test_markdown.py`

### Step 1: Write the failing test

```python
# tests/exporters/handlers/utils/test_markdown.py
"""tests for markdown to Apple Notes HTML conversion."""

from chatgpt2applenotes.exporters.handlers.utils.markdown import markdown_to_html


def test_converts_bold():
    """converts **bold** to <b>."""
    result = markdown_to_html("This is **bold** text")
    assert "<b>bold</b>" in result


def test_converts_italic():
    """converts *italic* to <i>."""
    result = markdown_to_html("This is *italic* text")
    assert "<i>italic</i>" in result


def test_converts_paragraphs_to_divs():
    """converts paragraphs to divs for Apple Notes."""
    result = markdown_to_html("First paragraph\n\nSecond paragraph")
    assert "<div>" in result
    assert "</div>" in result
    assert "<p>" not in result


def test_converts_inline_code():
    """converts inline code to <tt>."""
    result = markdown_to_html("Use `code` here")
    assert "<tt>code</tt>" in result


def test_converts_code_blocks():
    """converts code blocks to <pre>."""
    result = markdown_to_html("```\ncode block\n```")
    assert "<pre>" in result
    assert "</pre>" in result


def test_preserves_latex():
    """preserves LaTeX without markdown processing."""
    result = markdown_to_html("Formula $a_1$ here")
    assert "$a_1$" in result
    # underscore should not become <i>
    assert "<i>1</i>" not in result


def test_converts_unordered_lists():
    """converts unordered lists with bullet markers."""
    result = markdown_to_html("- item 1\n- item 2")
    # should use div with bullet, not native <ul>/<li>
    assert "<ul>" not in result


def test_converts_ordered_lists():
    """converts ordered lists with number markers."""
    result = markdown_to_html("1. first\n2. second")
    # should use div with number, not native <ol>/<li>
    assert "<ol>" not in result
    assert "1." in result or "1.\t" in result


def test_renders_tables():
    """renders markdown tables."""
    md = "| A | B |\n|---|---|\n| 1 | 2 |"
    result = markdown_to_html(md)
    assert "<table>" in result


def test_escapes_html():
    """escapes HTML in input."""
    result = markdown_to_html("<script>alert('xss')</script>")
    assert "<script>" not in result
    assert "&lt;script&gt;" in result
```

### Step 2: Run test to verify it fails

Run: `pytest tests/exporters/handlers/utils/test_markdown.py -v`
Expected: FAIL with ModuleNotFoundError

### Step 3: Write implementation

```python
# chatgpt2applenotes/exporters/handlers/utils/markdown.py
"""markdown to Apple Notes HTML conversion."""

import html as html_lib
from typing import Any, cast

from markdown_it import MarkdownIt

from chatgpt2applenotes.exporters.handlers.utils.latex import (
    protect_latex,
    restore_latex,
)
from chatgpt2applenotes.exporters.handlers.utils.spacing import add_block_spacing


def markdown_to_html(text: str) -> str:
    """
    converts markdown to Apple Notes-compatible HTML.

    Args:
        text: markdown text

    Returns:
        Apple Notes-compatible HTML
    """
    protected_text, latex_matches = protect_latex(text)

    md = MarkdownIt()
    md.enable("table")
    md.disable("html_inline")
    md.disable("html_block")

    renderer: Any = md.renderer
    original_render_token = renderer.renderToken

    # tracks list state for numbered lists
    list_state: list[tuple[str, int]] = []

    def _handle_list_token(tag: str, nesting: int) -> str:
        """handles ul/ol/li tokens for Apple Notes list rendering."""
        if tag in ("ul", "ol"):
            if nesting == 1:
                list_state.append((tag, 0))
            elif list_state:
                list_state.pop()
            return ""
        # li tag
        if nesting != 1:
            return "</div>\n"
        # opening li
        if list_state and list_state[-1][0] == "ol":
            list_type, counter = list_state[-1]
            list_state[-1] = (list_type, counter + 1)
            return f"<div>{counter + 1}.\t"
        return "<div>\u2022\t"

    def custom_render_token(tokens: Any, idx: int, options: Any, env: Any) -> str:
        """custom token renderer for Apple Notes compatibility."""
        token = tokens[idx]

        if token.tag in ("ul", "ol", "li"):
            return _handle_list_token(token.tag, token.nesting)

        tag_map = {"p": "div", "strong": "b", "em": "i", "code": "tt"}
        if token.tag in tag_map:
            token.tag = tag_map[token.tag]

        return cast(str, original_render_token(tokens, idx, options, env))

    renderer.renderToken = custom_render_token

    def render_code_block(tokens: Any, idx: int, _options: Any, _env: Any) -> str:
        token = tokens[idx]
        escaped = html_lib.escape(token.content)
        return f"<pre>{escaped}</pre>\n"

    renderer.rules["code_block"] = render_code_block
    renderer.rules["fence"] = render_code_block

    def render_image(tokens: Any, idx: int, _options: Any, _env: Any) -> str:
        token = tokens[idx]
        src = token.attrGet("src") or ""
        escaped_src = html_lib.escape(src)
        return f'<div><img src="{escaped_src}" style="max-width: 100%; max-height: 100%;"></div>\n'

    renderer.rules["image"] = render_image

    result = cast(str, md.render(protected_text))
    result = restore_latex(result, latex_matches) if latex_matches else result

    return add_block_spacing(result)
```

### Step 4: Run test to verify it passes

Run: `pytest tests/exporters/handlers/utils/test_markdown.py -v`
Expected: PASS

### Step 5: Update utils/init.py for convenience imports

```python
# chatgpt2applenotes/exporters/handlers/utils/init.py
"""utility modules for content handlers."""

from chatgpt2applenotes.exporters.handlers.utils.citations import render_citations
from chatgpt2applenotes.exporters.handlers.utils.latex import protect_latex, restore_latex
from chatgpt2applenotes.exporters.handlers.utils.markdown import markdown_to_html
from chatgpt2applenotes.exporters.handlers.utils.spacing import add_block_spacing

__all__ = [
    "protect_latex",
    "restore_latex",
    "markdown_to_html",
    "render_citations",
    "add_block_spacing",
]
```

### Step 6: Commit

```bash
git add chatgpt2applenotes/exporters/handlers/utils/ tests/exporters/handlers/utils/
git commit -m "feat(handlers): add markdown conversion utilities"
```

---

## Task 6: Create part registry

**Files:**

- Create: `chatgpt2applenotes/exporters/handlers/parts/init.py`
- Create: `tests/exporters/handlers/parts/init.py`
- Create: `tests/exporters/handlers/parts/test_part_registry.py`

### Step 1: Write the failing test

```python
# tests/exporters/handlers/parts/test_part_registry.py
"""tests for multimodal part registry."""

from chatgpt2applenotes.exporters.handlers import RenderContext
from chatgpt2applenotes.exporters.handlers.parts import PartRegistry, part_handler


def test_part_handler_decorator_registers():
    """@part_handler decorator registers part handler."""
    registry = PartRegistry()

    @part_handler("test_part", registry=registry)
    class TestPartHandler:
        def render(self, part, ctx):
            return "<span>test</span>"

    assert "test_part" in registry._handlers


def test_part_registry_dispatches():
    """PartRegistry.render dispatches to correct handler."""
    registry = PartRegistry()

    @part_handler("audio_transcription", registry=registry)
    class AudioHandler:
        def render(self, part, ctx):
            return f"<i>{part.get('text')}</i>"

    ctx = RenderContext()
    result = registry.render(
        {"content_type": "audio_transcription", "text": "hello"}, ctx
    )
    assert result == "<i>hello</i>"


def test_part_registry_returns_none_for_unknown():
    """PartRegistry.render returns None for unknown part type."""
    registry = PartRegistry()
    ctx = RenderContext()
    result = registry.render({"content_type": "unknown_part"}, ctx)
    assert result is None


def test_internal_part_skipped_without_flag():
    """internal part handler skipped when render_internals=False."""
    registry = PartRegistry()

    @part_handler("audio_asset_pointer", internal=True, registry=registry)
    class AudioAssetHandler:
        def render(self, part, ctx):
            return "[audio]"

    ctx = RenderContext(render_internals=False)
    result = registry.render({"content_type": "audio_asset_pointer"}, ctx)
    assert result is None


def test_internal_part_rendered_with_flag():
    """internal part handler renders when render_internals=True."""
    registry = PartRegistry()

    @part_handler("audio_asset_pointer", internal=True, registry=registry)
    class AudioAssetHandler:
        def render(self, part, ctx):
            return "[audio]"

    ctx = RenderContext(render_internals=True)
    result = registry.render({"content_type": "audio_asset_pointer"}, ctx)
    assert result == "[audio]"
```

### Step 2: Run test to verify it fails

Run: `pytest tests/exporters/handlers/parts/test_part_registry.py -v`
Expected: FAIL with ModuleNotFoundError

### Step 3: Write implementation

```python
# chatgpt2applenotes/exporters/handlers/parts/init.py
"""part registry for multimodal content handlers."""

from typing import Any, Protocol, TypeVar

from chatgpt2applenotes.exporters.handlers import RenderContext


class PartHandler(Protocol):
    """protocol for multimodal part handlers."""

    content_type: str | list[str]
    internal: bool

    def render(self, part: dict[str, Any], ctx: RenderContext) -> str: ...


class PartRegistry:
    """registry for multimodal part handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, PartHandler] = {}

    def register(self, handler_instance: PartHandler) -> None:
        """registers a part handler for its content type(s)."""
        types = (
            handler_instance.content_type
            if isinstance(handler_instance.content_type, list)
            else [handler_instance.content_type]
        )
        for t in types:
            self._handlers[t] = handler_instance

    def render(
        self, part: dict[str, Any], ctx: RenderContext
    ) -> str | None:
        """
        renders a part using the appropriate handler.

        Args:
            part: part dict with content_type key
            ctx: render context with flags

        Returns:
            rendered HTML string, or None if unhandled/skipped
        """
        content_type = part.get("content_type")
        if not content_type:
            return None

        handler_instance = self._handlers.get(content_type)
        if not handler_instance:
            return None

        if handler_instance.internal and not ctx.render_internals:
            return None

        return handler_instance.render(part, ctx)


# global part registry
part_registry = PartRegistry()

T = TypeVar("T")


def part_handler(
    content_type: str | list[str],
    internal: bool = False,
    registry: PartRegistry = part_registry,
):
    """
    decorator to register a part handler.

    Args:
        content_type: part content type string or list
        internal: if True, only render when render_internals=True
        registry: registry to register with (defaults to global)

    Returns:
        decorator function
    """

    def decorator(cls: type[T]) -> type[T]:
        cls.content_type = content_type  # type: ignore[attr-defined]
        cls.internal = internal  # type: ignore[attr-defined]
        registry.register(cls())  # type: ignore[arg-type]
        return cls

    return decorator
```

### Step 4: Run test to verify it passes

Run: `pytest tests/exporters/handlers/parts/test_part_registry.py -v`
Expected: PASS

### Step 5: Commit

```bash
mkdir -p tests/exporters/handlers/parts
touch tests/exporters/handlers/parts/init.py
git add chatgpt2applenotes/exporters/handlers/parts/ tests/exporters/handlers/parts/
git commit -m "feat(handlers): add part registry for multimodal content"
```

---

## Task 7: Create audio part handlers

**Depends on:** Task 6

**Files:**

- Create: `chatgpt2applenotes/exporters/handlers/parts/audio.py`
- Create: `tests/exporters/handlers/parts/test_audio.py`

### Step 1: Write the failing test

```python
# tests/exporters/handlers/parts/test_audio.py
"""tests for audio part handlers."""

import pytest

from chatgpt2applenotes.exporters.handlers import RenderContext
from chatgpt2applenotes.exporters.handlers.parts.audio import (
    AudioTranscriptionHandler,
    AudioAssetHandler,
    RealTimeAudioVideoHandler,
)


@pytest.fixture
def ctx():
    return RenderContext()


@pytest.fixture
def ctx_internals():
    return RenderContext(render_internals=True)


class TestAudioTranscriptionHandler:
    def test_renders_transcription(self, ctx):
        """renders audio transcription as italicized quoted text."""
        handler = AudioTranscriptionHandler()
        part = {"content_type": "audio_transcription", "text": "Hello world"}
        result = handler.render(part, ctx)
        assert "<i>" in result
        assert "Hello world" in result
        assert '"' in result  # quoted

    def test_escapes_html(self, ctx):
        """escapes HTML in transcription text."""
        handler = AudioTranscriptionHandler()
        part = {"content_type": "audio_transcription", "text": "<script>bad</script>"}
        result = handler.render(part, ctx)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


class TestAudioAssetHandler:
    def test_renders_placeholder(self, ctx_internals):
        """renders audio asset as placeholder."""
        handler = AudioAssetHandler()
        part = {"content_type": "audio_asset_pointer", "asset_pointer": "sediment://..."}
        result = handler.render(part, ctx_internals)
        assert "[Audio" in result or "audio" in result.lower()

    def test_is_internal(self):
        """audio asset handler is marked as internal."""
        assert AudioAssetHandler.internal is True


class TestRealTimeAudioVideoHandler:
    def test_renders_placeholder(self, ctx_internals):
        """renders real-time audio/video as placeholder."""
        handler = RealTimeAudioVideoHandler()
        part = {"content_type": "real_time_user_audio_video_asset_pointer"}
        result = handler.render(part, ctx_internals)
        assert "[" in result  # placeholder indicator

    def test_is_internal(self):
        """real-time handler is marked as internal."""
        assert RealTimeAudioVideoHandler.internal is True
```

### Step 2: Run test to verify it fails

Run: `pytest tests/exporters/handlers/parts/test_audio.py -v`
Expected: FAIL with ModuleNotFoundError

### Step 3: Write implementation

```python
# chatgpt2applenotes/exporters/handlers/parts/audio.py
"""audio part handlers for multimodal content."""

import html
from typing import Any

from chatgpt2applenotes.exporters.handlers import RenderContext
from chatgpt2applenotes.exporters.handlers.parts import part_handler


@part_handler("audio_transcription")
class AudioTranscriptionHandler:
    """renders audio transcription text."""

    def render(self, part: dict[str, Any], ctx: RenderContext) -> str:
        text = part.get("text", "")
        escaped = html.escape(text)
        return f'<div><i>"{escaped}"</i></div>'


@part_handler("audio_asset_pointer", internal=True)
class AudioAssetHandler:
    """renders audio asset pointer placeholder."""

    def render(self, part: dict[str, Any], ctx: RenderContext) -> str:
        return "<div><i>[Audio attachment]</i></div>"


@part_handler("real_time_user_audio_video_asset_pointer", internal=True)
class RealTimeAudioVideoHandler:
    """renders real-time audio/video pointer placeholder."""

    def render(self, part: dict[str, Any], ctx: RenderContext) -> str:
        return "<div><i>[Voice/video input]</i></div>"
```

### Step 4: Run test to verify it passes

Run: `pytest tests/exporters/handlers/parts/test_audio.py -v`
Expected: PASS

### Step 5: Commit

```bash
git add chatgpt2applenotes/exporters/handlers/parts/audio.py tests/exporters/handlers/parts/test_audio.py
git commit -m "feat(handlers): add audio part handlers"
```

---

## Task 8: Create text content handler

**Depends on:** Tasks 4, 5

**Files:**

- Create: `chatgpt2applenotes/exporters/handlers/text.py`
- Create: `tests/exporters/handlers/test_text.py`

### Step 1: Write the failing test

```python
# tests/exporters/handlers/test_text.py
"""tests for text content handler."""

import pytest

from chatgpt2applenotes.exporters.handlers import RenderContext
from chatgpt2applenotes.exporters.handlers.text import TextHandler


@pytest.fixture
def handler():
    return TextHandler()


@pytest.fixture
def ctx():
    return RenderContext()


def test_renders_simple_text(handler, ctx):
    """renders simple text content."""
    content = {"content_type": "text", "parts": ["Hello world"]}
    result = handler.render(content, None, ctx)
    assert "Hello world" in result


def test_renders_markdown(handler, ctx):
    """renders markdown formatting."""
    content = {"content_type": "text", "parts": ["**bold** and *italic*"]}
    result = handler.render(content, None, ctx)
    assert "<b>bold</b>" in result
    assert "<i>italic</i>" in result


def test_joins_multiple_parts(handler, ctx):
    """joins multiple parts with newlines."""
    content = {"content_type": "text", "parts": ["part 1", "part 2"]}
    result = handler.render(content, None, ctx)
    assert "part 1" in result
    assert "part 2" in result


def test_preserves_latex(handler, ctx):
    """preserves LaTeX in text content."""
    content = {"content_type": "text", "parts": ["Formula $a_1$ here"]}
    result = handler.render(content, None, ctx)
    assert "$a_1$" in result


def test_renders_citations(handler, ctx):
    """renders citations from metadata."""
    content = {"content_type": "text", "parts": ["See this. \ue200cite\ue202t0\ue201"]}
    metadata = {
        "content_references": [
            {
                "matched_text": "\ue200cite\ue202t0\ue201",
                "items": [{"url": "https://example.com", "attribution": "Example"}],
            }
        ]
    }
    result = handler.render(content, metadata, ctx)
    assert '<a href="https://example.com">Example</a>' in result


def test_removes_footnote_marks(handler, ctx):
    """removes footnote marks like citation patterns."""
    content = {"content_type": "text", "parts": ["Text\u301011\u2020(source)\u3011here"]}
    result = handler.render(content, None, ctx)
    # the \u3010...\u3011 pattern should be removed
    assert "\u3010" not in result


def test_handles_empty_parts(handler, ctx):
    """handles empty or None parts gracefully."""
    content = {"content_type": "text", "parts": None}
    result = handler.render(content, None, ctx)
    assert result is not None
```

### Step 2: Run test to verify it fails

Run: `pytest tests/exporters/handlers/test_text.py -v`
Expected: FAIL with ModuleNotFoundError

### Step 3: Write implementation

```python
# chatgpt2applenotes/exporters/handlers/text.py
"""text content handler."""

import re
from typing import Any

from chatgpt2applenotes.exporters.handlers import RenderContext, handler
from chatgpt2applenotes.exporters.handlers.utils.citations import render_citations
from chatgpt2applenotes.exporters.handlers.utils.markdown import markdown_to_html

FOOTNOTE_PATTERN = re.compile(r"[\u3010\u3011\uff3b\uff3d]\d+\u2020\([^)]+\)[\u3010\u3011\uff3b\uff3d]")


@handler("text")
class TextHandler:
    """renders text content type as markdown."""

    def render(
        self,
        content: dict[str, Any],
        metadata: dict[str, Any] | None,
        ctx: RenderContext,
    ) -> str:
        parts = content.get("parts") or []
        text = "\n".join(str(p) for p in parts if p)
        text = FOOTNOTE_PATTERN.sub("", text)
        html = markdown_to_html(text)
        return render_citations(html, metadata)
```

### Step 4: Run test to verify it passes

Run: `pytest tests/exporters/handlers/test_text.py -v`
Expected: PASS

### Step 5: Commit

```bash
git add chatgpt2applenotes/exporters/handlers/text.py tests/exporters/handlers/test_text.py
git commit -m "feat(handlers): add text content handler"
```

---

## Tasks 9-15: Additional Handlers (Pattern Follows Task 8)

For brevity, Tasks 9-15 follow the same pattern as Task 8. Each creates:

- Handler module in `chatgpt2applenotes/exporters/handlers/`
- Test file in `tests/exporters/handlers/`

**Task 9:** `multimodal.py` - dispatches to part registry, handles string parts
**Task 10:** `code.py` - renders as `<pre>` block
**Task 11:** `execution.py` - images from metadata or text output
**Task 12:** `browsing.py` - tether_quote, tether_browsing_display, sonic_webpage
**Task 13:** `internals.py` - thoughts, reasoning_recap, user/model_editable_context (internal=True)
**Task 14:** `errors.py` - system_error
**Task 15:** `app_context.py` - app_pairing_content

---

## Task 16: Integrate handlers into html_renderer.py

**Depends on:** Tasks 8-15

**Files:**

- Modify: `chatgpt2applenotes/exporters/html_renderer.py`

### Step 1: Run existing integration tests

Run: `pytest tests/test_apple_notes_content_types.py -v`
Expected: PASS (baseline)

### Step 2: Refactor html_renderer.py to use registry

Replace `_render_message_content` with registry dispatch while preserving the author-specific logic for user messages.

### Step 3: Run integration tests to verify compatibility

Run: `pytest tests/test_apple_notes_content_types.py -v`
Expected: PASS (unchanged behavior)

### Step 4: Commit

```bash
git add chatgpt2applenotes/exporters/html_renderer.py
git commit -m "refactor(renderer): integrate handler registry"
```

---

## Task 17: Add --render-internals CLI flag

**Depends on:** Task 16

**Files:**

- Modify: `chatgpt2applenotes/init.py`
- Modify: `chatgpt2applenotes/sync.py`
- Modify: `chatgpt2applenotes/exporters/apple_notes.py`
- Create: `tests/test_cli_render_internals.py`

### Step 1: Write the failing test

```python
# tests/test_cli_render_internals.py
"""tests for --render-internals CLI flag."""

from chatgpt2applenotes import main


def test_render_internals_flag_accepted(tmp_path, monkeypatch):
    """--render-internals flag is accepted by CLI."""
    # create a minimal JSON file
    json_file = tmp_path / "test.json"
    json_file.write_text('{"id": "1", "title": "T", "mapping": {}}')

    # should not raise
    result = main([str(json_file), "--render-internals", "--dry-run"])
    assert result == 0
```

### Step 2: Add flag to CLI

Modify `chatgpt2applenotes/init.py` to add the `--render-internals` argument.

### Step 3: Thread flag through sync.py and apple_notes.py

Pass `render_internals` through the call chain to `RenderContext`.

### Step 4: Run test to verify it passes

Run: `pytest tests/test_cli_render_internals.py -v`
Expected: PASS

### Step 5: Commit

```bash
git add chatgpt2applenotes/init.py chatgpt2applenotes/sync.py chatgpt2applenotes/exporters/apple_notes.py tests/test_cli_render_internals.py
git commit -m "feat(cli): add --render-internals flag"
```

---

## Task 18: Final integration test verification

**Depends on:** Task 17

### Step 1: Run all tests

Run: `pytest -v`
Expected: All PASS

### Step 2: Run with real data (manual verification)

```bash
chatgpt2applenotes /path/to/export.json TestFolder --dry-run
chatgpt2applenotes /path/to/export.json TestFolder --dry-run --render-internals
```

### Step 3: Final commit

```bash
git add -A
git commit -m "test: verify full integration"
```
