# Apple Notes Renderer Design

**Date:** 2026-01-11
**Author:** Claude & User
**Status:** Approved for Implementation

## Overview

Render ChatGPT conversations to Apple Notes format. This design pivots from the byte-for-byte TypeScript port approach to a direct Apple Notes renderer that produces HTML compatible with Apple Notes' import format.

## Goals

1. Convert ChatGPT JSON exports to Apple Notes-compatible HTML
2. Support text, markdown, images, tables, and code blocks
3. File-based output first (manual import), then direct Apple Notes integration
4. Preserve conversation metadata for updates/overwrites

## Architecture

### Overall Structure

```
chatgpt2applenotes/exporters/
├── base.py          (existing - abstract Exporter)
├── html.py          (existing - keep for reference)
└── apple_notes.py   (new - Apple Notes exporter)
```

### Key Components

#### 1. AppleNotesExporter

Main exporter class with configurable target:

- **Constructor parameter:** `target: Literal["file", "notes"]`
  - `target="file"`: writes HTML files with `<html><body>` wrapper
  - `target="notes"`: writes directly to Apple Notes (no wrapper tags)
- **File behavior:** always overwrites existing files
- **Notes behavior:** finds existing note by conversation ID, overwrites or creates new

#### 2. AppleNotesRenderer

Converts conversation data to Apple Notes HTML format:

- Renders markdown in message content to Apple Notes HTML
- Handles images from multimodal content
- Maintains Apple Notes structure (`<div>` wrappers, spacing)
- Adds metadata for update detection

#### 3. Message Structure

One note per conversation:

- **Note title:** conversation title
- **Note body:** all messages in chronological order
- **Each message:** shows author role + formatted content

## Apple Notes HTML Format

### Structure Requirements

Based on reference file analysis:

- Everything wrapped in `<div>` tags
- `<div><br></div>` for blank lines between sections
- Simple inline formatting: `<b>`, `<i>`, `<tt>` (code), `<strike>`
- Lists: `<ul>`, `<ol>` with proper nesting
- Tables: `<object><table>` with specific styling
- Links: standard `<a href="...">` tags
- Images: `<img src="data:image/...;base64,..."/>` with max-width/height

### Conversation Template

```html
<div><h1>Conversation Title</h1></div>
<div style="font-size: x-small; color: gray;">
  conv-123 | Updated: 2026-01-11 15:30
</div>
<div><br></div>
<div><h2>User</h2></div>
<div style="font-size: x-small; color: gray;">msg-456</div>
<div>[formatted message content]</div>
<div><br></div>
<div><h2>Assistant</h2></div>
<div style="font-size: x-small; color: gray;">msg-789</div>
<div>[formatted message content]</div>
<div><br></div>
<!-- repeat for each message -->
```

### Markdown to Apple Notes Mapping

| Markdown | Apple Notes HTML |
|----------|------------------|
| `# heading` | `<div><h1>heading</h1></div>` |
| `## heading` | `<div><h2>heading</h2></div>` |
| `**bold**` | `<b>bold</b>` |
| `*italic*` | `<i>italic</i>` |
| `` `code` `` | `<tt>code</tt>` |
| ` ```lang\ncode\n``` ` | `<div><tt>code</tt></div>` |
| `- item` | `<ul><li>item</li></ul>` |
| `1. item` | `<ol><li>item</li></ol>` |
| `[text](url)` | `<a href="url">text</a>` |
| Tables | `<object><table>...</table></object>` |

## Data Flow

### Processing Pipeline

```
JSON → Parser → Conversation → AppleNotesExporter → HTML
                                         ↓
                              AppleNotesRenderer
                                         ↓
                          [file] or [Apple Notes app]
```

### Content Type Handling

From our parser, `message.content` is a dict with:
- `content_type`: "text", "multimodal_text", etc.
- `parts`: list of strings or objects

#### Processing by Content Type

1. **"text":**
   - `parts` = list of strings
   - Join parts, render as markdown → Apple Notes HTML

2. **"multimodal_text":**
   - `parts` = mixed list of strings and objects
   - String parts: render as markdown
   - Object parts (images): extract and render as `<img>` tags
   - Preserve order of text and images

3. **Other types** ("model_editable_context", etc.):
   - Skip or render as plain text

### Image Handling

For image objects in multimodal_text parts:
- Extract image data (base64 or URL from the object)
- Render as: `<img style="max-width: 100%; max-height: 100%;" src="data:image/...;base64,..."/>`
- Add `<div><br></div>` spacing after images

## Metadata Strategy

### Conversation-Level Metadata

Displayed in small gray text at top of note:
- Conversation ID
- Update timestamp

Format: `conv-123 | Updated: 2026-01-11 15:30`

### Message-Level Metadata

Displayed in small gray text before each message:
- Message ID

Format: `msg-456`

### Purpose

- **File target:** informational only
- **Notes target:** used to find and update existing notes

## Error Handling

### Content Errors

1. **Missing/Invalid Content:**
   - Messages with no content → skip (already filtered by parser)
   - Unrecognized content_type → log warning, render as plain text
   - Markdown rendering handled by markdown-it-py

2. **Image Handling Failures:**
   - Missing image data → insert placeholder: `<div>[Image unavailable]</div>`
   - Invalid base64 → log error, insert placeholder
   - Unsupported image format → render as-is, let Apple Notes decide

3. **Apple Notes Writing (target="notes"):**
   - Apple Notes not running → raise clear error message
   - Permission denied → raise error with instructions
   - Note creation fails → log error, continue with next conversation

### Edge Cases

1. **Empty conversations** (no messages after filtering) → skip, log warning
2. **Very long conversations** → render all (Apple Notes handles long notes)
3. **Special characters in title** → sanitize for filesystem (file target only)
4. **Duplicate conversation titles** (file target) → append timestamp for uniqueness
5. **Duplicate conversation titles** (notes target) → use conversation ID for matching
6. **Nested lists/tables** → preserve structure (Apple Notes supports it)

## File Target Specifics

- **Output directory:** configurable, default `output/apple-notes/`
- **Filename:** `{conversation_title}.html` (sanitized)
- **Overwrite behavior:** always overwrite
- **HTML wrapper:** `<html><body>{content}</body></html>`

## Testing Strategy

### Unit Tests (`tests/test_apple_notes.py`)

- Markdown → Apple Notes HTML conversion
- Different content types (text, multimodal_text)
- List rendering (bulleted, numbered, nested)
- Table rendering
- Image handling (with/without data)
- Metadata formatting (conversation ID, timestamps, message IDs)
- Special characters in titles/content

### Integration Tests

- File target: verify HTML files created with correct structure
- Parse real conversation → render → validate HTML structure
- Test with conversations containing images
- Test edge cases: empty messages, unknown content types

### Manual Testing (Apple Notes)

- File-based: generate HTML, manually import to Apple Notes
- Verify formatting renders correctly
- Test update/overwrite behavior
- Then implement direct Apple Notes integration

## Implementation Plan

### Phase 1: File-Based Renderer (Current Branch)

1. Create `chatgpt2applenotes/exporters/apple_notes.py` with `AppleNotesExporter`
2. Implement Apple Notes HTML renderer (markdown → Apple Notes format)
3. Handle text and multimodal content types
4. Add metadata rendering (conversation ID, timestamps, message IDs)
5. File target: wrap in `<html><body>` tags, save to files
6. Unit tests for rendering logic
7. Integration tests with real conversations

### Phase 2: Direct Apple Notes Integration (Future)

1. Implement AppleScript/JXA integration for Apple Notes
2. Read existing notes to find matches by conversation ID
3. Update existing vs create new notes
4. Remove `<html><body>` wrapper for direct writing
5. Error handling for Apple Notes not running, permissions, etc.

## Success Criteria (Phase 1)

- ✅ Render ChatGPT conversations to Apple Notes HTML format
- ✅ Support text, markdown, lists, tables, code blocks
- ✅ Handle images from multimodal content
- ✅ Generate files that can be manually imported to Apple Notes
- ✅ All tests pass
- ✅ Validate with real conversation data

## Future Enhancements

- Direct Apple Notes integration (Phase 2)
- Batch processing of multiple conversations
- CLI interface for export operations
- Progress reporting for large exports
- Configurable output formatting
- Support for other content types as discovered
