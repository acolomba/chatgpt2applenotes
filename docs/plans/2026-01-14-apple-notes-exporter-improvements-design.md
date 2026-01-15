# Apple Notes Exporter Improvements

## Background

This design documents improvements to the Apple Notes exporter identified by comparing it with the upstream TypeScript HTML exporter from chatgpt-exporter. The Python codebase was ported from that project, so the data structures are similar.

## Improvements

### 1. Code Block Line Breaks (High Priority)

**Problem:** Code blocks use `<div><tt>...</tt></div>` which collapses whitespace. Newlines in code are not preserved.

**Current code (lines 533-542):**

```python
def render_fence(tokens: Any, idx: int, _options: Any, _env: Any) -> str:
    token = tokens[idx]
    return f"<div><tt>{html_lib.escape(token.content)}</tt></div>\n"
```

**Solution options to try:**

1. Use `<pre>` tag if Apple Notes supports it
2. Convert newlines to `<br>` within `<tt>`
3. Use CSS `white-space: pre` on the `<tt>` element
4. Split into multiple `<div><tt>` elements per line

**Implementation:** Test each approach in Apple Notes to determine which renders correctly.

### 2. Image Asset Pointer Handling (High Priority)

**Problem:** `image_asset_pointer` parts in multimodal content are not rendered. The TypeScript exporter handles these with height/width attributes.

**TypeScript reference:**

```typescript
if (part.content_type === 'image_asset_pointer')
    return `<img src="${part.asset_pointer}" height="${part.height}" width="${part.width}" />`
```

**Current code (lines 596-610):** Only handles string parts and `audio_transcription`.

**Solution:** Add handling for `image_asset_pointer` parts in `_render_multimodal_content()`:

```python
elif isinstance(part, dict) and part.get("content_type") == "image_asset_pointer":
    src = html_lib.escape(part.get("asset_pointer", ""))
    height = part.get("height", "")
    width = part.get("width", "")
    html_parts.append(f'<div><img src="{src}" height="{height}" width="{width}" style="max-width: 100%;"></div>')
```

### 3. Footnote/Citation Marks (Medium Priority)

**Problem:** Citation marks like `【11†(PrintWiki)】` are stripped entirely. They should remain visible even if not linkable.

**Current code (line 664):**

```python
text = FOOTNOTE_PATTERN.sub("", text)  # removes citation marks
```

**Solution:** Remove this line. Keep citation marks in the rendered output.

### 4. LaTeX Protection in Code Blocks (Medium Priority)

**Problem:** LaTeX protection regex may incorrectly match `$variable` patterns inside code blocks.

**TypeScript approach (line 116):**

```typescript
const isCodeBlock = /```/.test(input)
if (!isCodeBlock && matches) {
    // only apply LaTeX protection if no code blocks
}
```

**Solution:** Skip LaTeX protection when the text contains code fences (triple backticks).

### 5. Unsupported Multimodal Content Fallback (Medium Priority)

**Problem:** Unknown multimodal part types are silently dropped.

**TypeScript reference:**

```typescript
return postProcess('[Unsupported multimodal content]')
```

**Solution:** Add fallback in `_render_multimodal_content()`:

```python
else:
    html_parts.append("<div>[Unsupported multimodal content]</div>")
```

### 6. Audio/Video Asset Pointers (Low Priority)

**Problem:** `audio_asset_pointer` and `real_time_user_audio_video_asset_pointer` are not explicitly handled.

**Solution:** Explicitly skip these types (they have no renderable content):

```python
elif isinstance(part, dict) and part.get("content_type") in (
    "audio_asset_pointer",
    "real_time_user_audio_video_asset_pointer"
):
    pass  # no renderable content
```

### 7. Execution Output Image Dimensions (Low Priority)

**Problem:** Images from execution output lack height/width attributes.

**Current code (lines 680-686):**

```python
parts.append(f'<div><img src="{escaped_url}" style="max-width: 100%;"></div>')
```

**Solution:** Extract and include dimensions:

```python
height = img.get("height", "")
width = img.get("width", "")
parts.append(f'<div><img src="{escaped_url}" height="{height}" width="{width}" style="max-width: 100%;"></div>')
```

### 8. LaTeX Rendering (Low Priority)

**Problem:** LaTeX is HTML-escaped and displayed as raw notation.

**Investigation needed:** Check if markdown-it-py has plugins for LaTeX rendering that produce static output (not requiring JavaScript like KaTeX/MathJax).

## Implementation Order

1. Code block line breaks (high impact on readability)
2. Image asset pointer handling (missing functionality)
3. Footnote marks (quick fix)
4. LaTeX in code blocks (edge case fix)
5. Multimodal fallback (defensive coding)
6. Audio/video pointers (explicit handling)
7. Execution output dimensions (minor enhancement)
8. LaTeX rendering (research needed)

## Testing

Each change should be tested by:

1. Exporting a conversation containing the relevant content type
2. Verifying correct rendering in Apple Notes
3. Verifying the sync/append functionality still works
