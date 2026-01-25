# Modular Content Handlers Design

## Overview

Refactor `chatgpt2applenotes` to use a modular handler architecture where each ChatGPT content type is rendered by a dedicated handler module. This improves testability, maintainability, and extensibility.

## Goals

- **Complete coverage** of user-visible content types
- **Custom rendering** per content type
- **Modular architecture** following open-closed principle
- **Unit tests per module** with real data fixtures
- **`--render-internals` flag** to optionally render internal content (thoughts, reasoning, context)
- **Integration tests unchanged** - existing behavior preserved

## Directory Structure

```text
chatgpt2applenotes/
├── __init__.py                    # CLI entry point (adds --render-internals)
├── sync.py                        # batch processing (passes render_internals)
├── core/
│   ├── models.py
│   └── parser.py
└── exporters/
    ├── apple_notes.py             # export orchestration
    ├── applescript.py
    ├── html_renderer.py           # orchestrator (dispatcher only)
    └── handlers/
        ├── __init__.py            # registry, decorator, RenderContext
        ├── text.py                # text content (markdown)
        ├── code.py                # code blocks
        ├── multimodal.py          # multimodal_text (dispatches to parts)
        ├── execution.py           # execution_output
        ├── browsing.py            # tether_quote, tether_browsing_display, sonic_webpage
        ├── internals.py           # thoughts, reasoning_recap, user/model_editable_context
        ├── errors.py              # system_error
        ├── app_context.py         # app_pairing_content (top-level)
        ├── parts/
        │   ├── __init__.py        # part registry and decorator
        │   ├── audio.py           # audio_transcription, audio_asset_pointer
        │   ├── image.py           # image_asset_pointer
        │   └── app.py             # app_pairing_content, real_time_user_audio_video_asset_pointer
        └── utils/
            ├── __init__.py        # re-exports
            ├── markdown.py        # markdown_to_html (Apple Notes customizations)
            ├── latex.py           # protect_latex, restore_latex
            ├── citations.py       # render_citations
            └── spacing.py         # add_block_spacing

tests/
├── exporters/
│   ├── handlers/
│   │   ├── test_text.py
│   │   ├── test_code.py
│   │   ├── test_multimodal.py
│   │   ├── test_execution.py
│   │   ├── test_browsing.py
│   │   ├── test_internals.py
│   │   ├── test_errors.py
│   │   ├── test_app_context.py
│   │   ├── parts/
│   │   │   ├── test_audio.py
│   │   │   ├── test_image.py
│   │   │   └── test_app.py
│   │   └── utils/
│   │       ├── test_markdown.py
│   │       ├── test_latex.py
│   │       ├── test_citations.py
│   │       └── test_spacing.py
│   └── test_html_renderer.py      # integration tests (existing)
└── fixtures/
    └── content_samples/           # real data samples for unit tests
```

## Handler Architecture

### RenderContext

```python
# handlers/__init__.py
from dataclasses import dataclass

@dataclass
class RenderContext:
    render_internals: bool = False
```

Configuration carrier passed through the render pipeline. Future flags added here.

### Handler Protocol

```python
from typing import Protocol

class ContentHandler(Protocol):
    content_type: str | list[str]
    internal: bool  # True = only render when render_internals is set

    def render(self, content: dict, metadata: dict | None, ctx: RenderContext) -> str: ...
```

### Registry with Flask-style Decorator

```python
class HandlerRegistry:
    _handlers: dict[str, ContentHandler] = {}

    @classmethod
    def register(cls, handler: ContentHandler) -> None:
        types = handler.content_type if isinstance(handler.content_type, list) else [handler.content_type]
        for t in types:
            cls._handlers[t] = handler

    @classmethod
    def render(cls, content: dict, metadata: dict | None, ctx: RenderContext) -> str | None:
        content_type = content.get("content_type", "text")
        handler = cls._handlers.get(content_type)

        if not handler:
            return None  # unhandled

        if handler.internal and not ctx.render_internals:
            return None  # skip internal content

        return handler.render(content, metadata, ctx)

def handler(content_type: str | list[str], internal: bool = False):
    """decorator to register a content handler."""
    def decorator(cls):
        cls.content_type = content_type
        cls.internal = internal
        HandlerRegistry.register(cls())
        return cls
    return decorator
```

### Handler Example

```python
# handlers/text.py
from . import handler, RenderContext
from .utils.markdown import markdown_to_html
from .utils.citations import render_citations

@handler("text")
class TextHandler:
    def render(self, content: dict, metadata: dict | None, ctx: RenderContext) -> str:
        parts = content.get("parts") or []
        text = "\n".join(str(p) for p in parts if p)
        html = markdown_to_html(text)
        return render_citations(html, metadata)
```

## Multimodal Parts Dispatch

`multimodal_text` contains a `parts` array with mixed types. Nested registry pattern:

```python
# handlers/parts/__init__.py
class PartRegistry:
    _handlers: dict[str, PartHandler] = {}

    @classmethod
    def render(cls, part: dict, ctx: RenderContext) -> str | None:
        content_type = part.get("content_type")
        handler = cls._handlers.get(content_type)
        if not handler:
            return None
        if handler.internal and not ctx.render_internals:
            return None
        return handler.render(part, ctx)

def part_handler(content_type: str | list[str], internal: bool = False):
    """decorator to register a part handler."""
    ...
```

```python
# handlers/multimodal.py
@handler("multimodal_text")
class MultimodalHandler:
    def render(self, content: dict, metadata: dict | None, ctx: RenderContext) -> str:
        parts = content.get("parts") or []
        html_parts = []

        for part in parts:
            if isinstance(part, str):
                html_parts.append(markdown_to_html(part))
            elif isinstance(part, dict):
                rendered = PartRegistry.render(part, ctx)
                if rendered:
                    html_parts.append(rendered)

        return "".join(html_parts)
```

## Utility Modules

Each utility is a separate module with pure functions:

### `utils/markdown.py`

- `markdown_to_html(text: str) -> str` - markdown-it with Apple Notes tag transformations (p->div, strong->b, em->i, code->tt, custom list rendering)

### `utils/latex.py`

- `protect_latex(text: str) -> tuple[str, list[str]]` - replaces LaTeX with placeholders
- `restore_latex(text: str, matches: list[str]) -> str` - restores LaTeX from placeholders

### `utils/citations.py`

- `render_citations(html: str, metadata: dict | None) -> str` - replaces citation markers with attribution links from `metadata.content_references`

### `utils/spacing.py`

- `add_block_spacing(html: str) -> str` - adds `<div><br></div>` between adjacent block elements

## Content Type Specifications

### User-Visible Content Types

#### `text` (2266 occurrences)

```json
{
  "content_type": "text",
  "parts": ["markdown string", "can be multiple parts"]
}
```

**Render:** markdown to Apple Notes HTML, with citation replacement.

#### `code` (309 occurrences)

```json
{
  "content_type": "code",
  "language": "python",
  "text": "code content",
  "response_format_name": null
}
```

**Render:** `<pre>` block.

#### `multimodal_text` (142 occurrences)

```json
{
  "content_type": "multimodal_text",
  "parts": ["string or object with content_type"]
}
```

**Render:** dispatch each part, concatenate results.

#### `execution_output` (14 occurrences)

```json
{
  "content_type": "execution_output",
  "text": "output text or traceback"
}
```

**Render:** images from `metadata.aggregate_result.messages` if present, else `<pre>` for text.

#### `tether_quote` (7 occurrences)

```json
{
  "content_type": "tether_quote",
  "url": "https://...",
  "domain": "example.com",
  "text": "quoted content"
}
```

**Render:** `<blockquote>`.

#### `tether_browsing_display` (8 occurrences)

```json
{
  "content_type": "tether_browsing_display",
  "result": "content with citation markers",
  "summary": null
}
```

**Render:** extract links from `metadata._cite_metadata.metadata_list`, render as blockquotes with anchors.

#### `sonic_webpage` (36 occurrences)

```json
{
  "content_type": "sonic_webpage",
  "url": "https://...",
  "domain": "example.com",
  "title": "Page Title",
  "text": "page content"
}
```

**Render:** title as link to URL.

#### `system_error` (1 occurrence)

```json
{
  "content_type": "system_error",
  "name": "ChatGPTAgentToolException",
  "text": "error message"
}
```

**Render:** warning indicator with error name.

#### `app_pairing_content` (1 occurrence, top-level)

```json
{
  "content_type": "app_pairing_content",
  "workspaces": [{"app_name": "Terminal", "title": "window title"}],
  "context_parts": [{"text": "content"}]
}
```

**Render:** app name + title, truncated context preview.

### Internal Content Types (require `--render-internals`)

#### `thoughts` (243 occurrences)

```json
{
  "content_type": "thoughts",
  "thoughts": [{"summary": "...", "content": "full reasoning"}]
}
```

**Render:** italicized thoughts with summary headers.

#### `reasoning_recap` (86 occurrences)

```json
{
  "content_type": "reasoning_recap",
  "content": "Thought for 2m 33s"
}
```

**Render:** italic indicator.

#### `user_editable_context` (108 occurrences)

```json
{
  "content_type": "user_editable_context",
  "user_profile": "...",
  "user_instructions": "..."
}
```

**Render:** summary or full text of user profile/instructions.

#### `model_editable_context` (165 occurrences)

```json
{
  "content_type": "model_editable_context",
  "model_set_context": ""
}
```

**Render:** if non-empty, show as ChatGPT memory note.

### Multimodal Part Types

#### `audio_transcription` (126 occurrences)

```json
{"content_type": "audio_transcription", "text": "...", "direction": "in|out"}
```

**Render:** italicized quoted text.

#### `audio_asset_pointer` (63 occurrences) - *internal*

```json
{"content_type": "audio_asset_pointer", "asset_pointer": "sediment://...", "format": "wav"}
```

**Render:** `[Audio attachment]` indicator.

#### `real_time_user_audio_video_asset_pointer` (63 occurrences) - *internal*

```json
{"content_type": "real_time_user_audio_video_asset_pointer", "audio_asset_pointer": {...}}
```

**Render:** `[Voice/video input]` indicator.

#### `image_asset_pointer` (12 occurrences)

```json
{"content_type": "image_asset_pointer", "asset_pointer": "file-service://...", "width": 1024, "height": 768}
```

**Render:** `[Image attachment]` indicator (asset URLs not accessible externally).

#### `app_pairing_content` (1 occurrence, as part)

Same as top-level, render as context summary.

## CLI Integration

```python
# __init__.py
@click.option(
    "--render-internals",
    is_flag=True,
    help="Render internal content (thoughts, reasoning, user/model context)",
)
def main(..., render_internals):
    process_conversations(..., render_internals=render_internals)
```

Flag flows: CLI -> `sync.py` -> `AppleNotesExporter` -> `AppleNotesRenderer` -> `RenderContext` -> handlers.

## Testing Strategy

### Unit Tests

Each handler has dedicated tests with fixtures from real export data:

```python
# tests/exporters/handlers/test_text.py
def test_simple_text(handler, ctx):
    content = {"content_type": "text", "parts": ["Hello **world**"]}
    result = handler.render(content, None, ctx)
    assert "<b>world</b>" in result

def test_text_with_latex_preserved(handler, ctx):
    content = {"content_type": "text", "parts": ["The formula $E=mc^2$ is famous"]}
    result = handler.render(content, None, ctx)
    assert "$E=mc^2$" in result
```

### Integration Tests

Existing tests in `test_html_renderer.py` continue testing the full pipeline. Output should be unchanged for default behavior.

### Test Fixtures

Real samples extracted from `/Users/acolomba/Downloads/chatgpt-export-json/` stored in `tests/fixtures/content_samples/`.

## Migration Path

1. Create `handlers/` directory structure
2. Extract utilities into `handlers/utils/` modules
3. Implement registry and decorator
4. Migrate each content type to its handler (one at a time)
5. Slim down `html_renderer.py` to dispatcher
6. Add `--render-internals` CLI flag
7. Write unit tests per handler
8. Verify integration tests pass
