# Citation Rendering Design

## Problem

ChatGPT conversations contain citation markers like `\ue200cite\ue202turn0search3\ue201` that reference web sources. Currently these render as garbled text (e.g., `îˆ€citeîˆ‚turn0search3îˆ"`).

## Solution

Replace citation markers with inline attribution links.

## Data Structure

Citation data is stored in `message.metadata['content_references']`:

```json
{
  "matched_text": "\ue200cite\ue202turn0search3\ue201",
  "items": [
    {
      "title": "How To Use Dictation on Your Mac",
      "url": "https://macmost.com/...",
      "attribution": "MacMost.com"
    }
  ],
  "supporting_websites": [
    {
      "title": "Mac Dictation Still Sucks...",
      "url": "https://www.reddit.com/...",
      "attribution": "Reddit"
    }
  ]
}
```

## Output Format

Single citation:

```html
(<a href="url">Attribution</a>)
```

Multi-citation:

```html
(<a href="url1">Attribution1</a>, <a href="url2">Attribution2</a>)
```

## Implementation

Location: `chatgpt2applenotes/exporters/html_renderer.py`

Add `_render_citations(text, metadata)` method that:

1. extracts `content_references` from message metadata
2. for each reference, builds replacement HTML from `items[].url` and `items[].attribution`
3. includes `supporting_websites` as additional comma-separated links
4. replaces `matched_text` patterns in content text

Call this method in `_render_text_content()` before markdown processing.

## Examples

Input text:

```text
You toggle dictation on and choose your language. \ue200cite\ue202turn0search3\ue201
```

Output:

```html
You toggle dictation on and choose your language. (<a href="https://macmost.com/...">MacMost.com</a>)
```

Input (multi-citation):

```text
Some users find it works for quick entries. \ue200cite\ue202turn1search2\ue202turn1search3\ue201
```

Output:

```html
Some users find it works for quick entries. (<a href="...">Intego</a>, <a href="...">Reddit</a>)
```
