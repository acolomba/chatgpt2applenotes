# Apple Notes Export Improvements Design

## Overview

Improve the Apple Notes exporter quality by adopting lessons learned from the TypeScript HTML exporter in `chatgpt-exporter`. The changes focus on content fidelity, message filtering, and visual styling.

## Background

This project's models and parser were ported from `chatgpt-exporter`. The TypeScript HTML exporter handles several content types and edge cases that the Python Apple Notes exporter currently doesn't support.

## Changes

### Content Fidelity

#### 1. Add missing content types

Support these content types in `_render_message_content`:

- `code`: render as fenced code block (code execution input)
- `execution_output`: render code results, including images from `metadata.aggregate_result`
- `tether_quote`: render as blockquote
- `tether_browsing_display`: render browsing results as blockquotes with links from `metadata._cite_metadata.metadata_list`

#### 2. Fix text part joining

Change line 573 from joining with space to joining with newline:

```python
# before
text = " ".join(str(p) for p in parts if p)

# after
text = "\n".join(str(p) for p in parts if p)
```

#### 3. Protect LaTeX from markdown processing

Before markdown processing, detect and preserve LaTeX patterns:

- `$...$` (inline)
- `$$...$$` (display)
- `\[...\]` (display)
- `\(...\)` (inline)

Use placeholder substitution (like TypeScript's `╬n╬` approach) to protect formulas, then restore after markdown conversion.

TODO: investigate rendering LaTeX in Apple Notes (possibly via pre-rendered images or MathML).

#### 4. Implement footnote cleanup

Remove citation marks like `【11†(PrintWiki)】` from assistant messages. The TypeScript implementation finds citations in `metadata.citations` by `cited_message_idx` and removes the mark.

#### 5. Add audio transcription support

In `_render_multimodal_content`, handle `audio_transcription` parts:

```python
if part.get("content_type") == "audio_transcription":
    text = part.get("text", "")
    html_parts.append(f'<div><i>"{html_lib.escape(text)}"</i></div>')
```

### Message Filtering

#### 6. Filter by recipient

Skip messages where `recipient != 'all'`. These are internal ChatGPT-to-tool communications.

Add check in `_generate_html` before rendering each message:

```python
recipient = message.metadata.get("recipient", "all")
if recipient != "all":
    continue
```

#### 7. Smarter tool message handling

Skip tool messages except when they contain user-visible content:

- `content_type == "multimodal_text"` (DALL-E images)
- `content_type == "execution_output"` with images in `metadata.aggregate_result.messages`

### Visual Styling

#### 8. Adopt TypeScript author labels

Replace role capitalization with descriptive labels:

```python
def _get_author_label(self, message: Message) -> str:
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

#### 9. Render user messages as plain text

User messages should be HTML-escaped but not processed through markdown:

```python
if message.author.role == "user":
    parts = message.content.get("parts") or []
    text = "\n".join(str(p) for p in parts if p)
    return f"<div>{html_lib.escape(text)}</div>"
```

This prevents unintended formatting from `*asterisks*` or `_underscores_` in user prompts.

## Not Included

- **Model indicator (GPT-3/GPT-4)**: not useful for archival purposes
- **Image dimensions**: Apple Notes attachments don't use width/height attributes

## Testing

- Test with conversations containing each new content type
- Verify LaTeX preservation with math-heavy conversations
- Confirm footnote marks are removed cleanly
- Check tool messages are filtered appropriately
