# Citation Rendering Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace ChatGPT citation markers with inline attribution links in exported HTML.

**Architecture:** Add a `_render_citations()` method to `AppleNotesRenderer` that extracts `content_references` from message metadata and replaces marker text with HTML links. Call this before markdown processing in `_render_text_content()`.

**Tech Stack:** Python, html module for escaping, existing html_renderer.py infrastructure.

---

## Task 1: Add single-citation rendering test

**Files:**

- Modify: `tests/test_apple_notes_content_types.py`

Step 1: Write the failing test

Add to `tests/test_apple_notes_content_types.py`:

```python
def test_renders_single_citation_as_link(tmp_path: Path) -> None:
    """citation markers are replaced with attribution links."""
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
                    "parts": ["See the guide. \ue200cite\ue202turn0search3\ue201"],
                },
                metadata={
                    "content_references": [
                        {
                            "matched_text": "\ue200cite\ue202turn0search3\ue201",
                            "items": [
                                {
                                    "url": "https://example.com/guide",
                                    "attribution": "Example.com",
                                }
                            ],
                        }
                    ]
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "See the guide." in html
    assert '<a href="https://example.com/guide">Example.com</a>' in html
    # marker should be gone
    assert "\ue200" not in html
    assert "turn0search3" not in html
```

Step 2: Run test to verify it fails

Run: `pytest tests/test_apple_notes_content_types.py::test_renders_single_citation_as_link -v`

Expected: FAIL - assertion error, marker text appears as-is or garbled

Step 3: Commit failing test

```bash
git add tests/test_apple_notes_content_types.py
git commit -m "test: add failing test for single citation rendering"
```

---

## Task 2: Implement single-citation rendering

**Files:**

- Modify: `chatgpt2applenotes/exporters/html_renderer.py:207-212`

Step 1: Add the `_render_citations` method

Add after line 62 (after `_tool_message_has_visible_content`):

```python
    def _render_citations(
        self, text: str, metadata: Optional[dict[str, Any]]
    ) -> str:
        """replaces citation markers with attribution links."""
        if not metadata:
            return text

        content_refs = metadata.get("content_references", [])
        if not content_refs:
            return text

        for ref in content_refs:
            matched_text = ref.get("matched_text", "")
            if not matched_text:
                continue

            items = ref.get("items", [])
            if not items:
                # no items, just remove the marker
                text = text.replace(matched_text, "")
                continue

            # build links from items
            links = []
            for item in items:
                url = item.get("url", "")
                attribution = item.get("attribution", "")
                if url and attribution:
                    escaped_url = html_lib.escape(url)
                    escaped_attr = html_lib.escape(attribution)
                    links.append(f'<a href="{escaped_url}">{escaped_attr}</a>')

            if links:
                replacement = "(" + ", ".join(links) + ")"
                text = text.replace(matched_text, replacement)
            else:
                text = text.replace(matched_text, "")

        return text
```

Step 2: Call `_render_citations` in `_render_text_content`

Modify `_render_text_content` (around line 207-212):

```python
    def _render_text_content(self, message: Message) -> str:
        """renders text content type as markdown."""
        parts = message.content.get("parts") or []
        text = "\n".join(str(p) for p in parts if p)
        text = FOOTNOTE_PATTERN.sub("", text)  # removes citation marks
        text = self._render_citations(text, message.metadata)  # render citations
        return self._markdown_to_apple_notes(text)
```

Step 3: Run test to verify it passes

Run: `pytest tests/test_apple_notes_content_types.py::test_renders_single_citation_as_link -v`

Expected: PASS

Step 4: Run all tests to check for regressions

Run: `pytest tests/ -v`

Expected: All tests pass

Step 5: Commit implementation

```bash
git add chatgpt2applenotes/exporters/html_renderer.py
git commit -m "feat: render single citations as inline attribution links"
```

---

## Task 3: Add multi-citation rendering test

**Files:**

- Modify: `tests/test_apple_notes_content_types.py`

Step 1: Write the failing test

Add to `tests/test_apple_notes_content_types.py`:

```python
def test_renders_multi_citation_as_comma_separated_links(tmp_path: Path) -> None:
    """multi-source citations render as comma-separated links."""
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
                        "It needs cleanup. \ue200cite\ue202turn1search2\ue202turn1search3\ue201"
                    ],
                },
                metadata={
                    "content_references": [
                        {
                            "matched_text": "\ue200cite\ue202turn1search2\ue202turn1search3\ue201",
                            "items": [
                                {
                                    "url": "https://intego.com/article",
                                    "attribution": "Intego",
                                    "supporting_websites": [
                                        {
                                            "url": "https://reddit.com/r/mac",
                                            "attribution": "Reddit",
                                        }
                                    ],
                                }
                            ],
                        }
                    ]
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "It needs cleanup." in html
    assert '<a href="https://intego.com/article">Intego</a>' in html
    assert '<a href="https://reddit.com/r/mac">Reddit</a>' in html
    # should be comma-separated
    assert "Intego</a>, <a" in html
    # marker should be gone
    assert "\ue200" not in html
```

Step 2: Run test to verify it fails

Run: `pytest tests/test_apple_notes_content_types.py::test_renders_multi_citation_as_comma_separated_links -v`

Expected: FAIL - supporting_websites not handled

Step 3: Commit failing test

```bash
git add tests/test_apple_notes_content_types.py
git commit -m "test: add failing test for multi-citation rendering"
```

---

## Task 4: Implement multi-citation (supporting_websites) rendering

**Files:**

- Modify: `chatgpt2applenotes/exporters/html_renderer.py`

Step 1: Update `_render_citations` to handle supporting_websites

Replace the link-building loop in `_render_citations`:

```python
            # build links from items and supporting_websites
            links = []
            for item in items:
                url = item.get("url", "")
                attribution = item.get("attribution", "")
                if url and attribution:
                    escaped_url = html_lib.escape(url)
                    escaped_attr = html_lib.escape(attribution)
                    links.append(f'<a href="{escaped_url}">{escaped_attr}</a>')

                # add supporting websites
                for support in item.get("supporting_websites", []):
                    s_url = support.get("url", "")
                    s_attr = support.get("attribution", "")
                    if s_url and s_attr:
                        escaped_url = html_lib.escape(s_url)
                        escaped_attr = html_lib.escape(s_attr)
                        links.append(f'<a href="{escaped_url}">{escaped_attr}</a>')
```

Step 2: Run test to verify it passes

Run: `pytest tests/test_apple_notes_content_types.py::test_renders_multi_citation_as_comma_separated_links -v`

Expected: PASS

Step 3: Run all tests

Run: `pytest tests/ -v`

Expected: All tests pass

Step 4: Commit implementation

```bash
git add chatgpt2applenotes/exporters/html_renderer.py
git commit -m "feat: render multi-citations with supporting websites"
```

---

## Task 5: Add test for citation without items (edge case)

**Files:**

- Modify: `tests/test_apple_notes_content_types.py`

Step 1: Write the test

```python
def test_removes_citation_marker_without_items(tmp_path: Path) -> None:
    """citation markers without items are removed cleanly."""
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
                    "parts": ["No source here. \ue200cite\ue202turn0search0\ue201"],
                },
                metadata={
                    "content_references": [
                        {
                            "matched_text": "\ue200cite\ue202turn0search0\ue201",
                            "items": [],
                        }
                    ]
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    assert "No source here." in html
    # marker should be removed, no link added
    assert "\ue200" not in html
    assert "turn0search0" not in html
    assert "<a href" not in html or "conv-123" in html  # only footer link ok
```

Step 2: Run test

Run: `pytest tests/test_apple_notes_content_types.py::test_removes_citation_marker_without_items -v`

Expected: PASS (already handled)

Step 3: Commit test

```bash
git add tests/test_apple_notes_content_types.py
git commit -m "test: add edge case test for citation without items"
```

---

## Task 6: End-to-end test with real JSON file

**Files:**

- Modify: `tests/test_apple_notes_content_types.py`

Step 1: Write the test

```python
def test_renders_citations_from_real_conversation_structure(tmp_path: Path) -> None:
    """citations render correctly with real ChatGPT export structure."""
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
                        "Enable in **System Settings**. \ue200cite\ue202turn0search3\ue201 "
                        "Accuracy varies. \ue200cite\ue202turn1search2\ue202turn1search3\ue201"
                    ],
                },
                metadata={
                    "content_references": [
                        {
                            "matched_text": "\ue200cite\ue202turn0search3\ue201",
                            "items": [
                                {
                                    "title": "How To Use Dictation",
                                    "url": "https://macmost.com/dictation",
                                    "attribution": "MacMost.com",
                                }
                            ],
                        },
                        {
                            "matched_text": "\ue200cite\ue202turn1search2\ue202turn1search3\ue201",
                            "items": [
                                {
                                    "title": "Dictation Tips",
                                    "url": "https://intego.com/tips",
                                    "attribution": "Intego",
                                    "supporting_websites": [
                                        {
                                            "title": "Discussion",
                                            "url": "https://reddit.com/r/mac",
                                            "attribution": "Reddit",
                                        }
                                    ],
                                }
                            ],
                        },
                    ]
                },
            )
        ],
    )

    exporter = AppleNotesExporter(target="file")
    output_dir = tmp_path / "notes"
    exporter.export(conversation, str(output_dir))

    html = (output_dir / "Test.html").read_text(encoding="utf-8")
    # text preserved
    assert "Enable in" in html
    assert "System Settings" in html
    assert "Accuracy varies." in html
    # first citation
    assert '<a href="https://macmost.com/dictation">MacMost.com</a>' in html
    # second citation with supporting site
    assert '<a href="https://intego.com/tips">Intego</a>' in html
    assert '<a href="https://reddit.com/r/mac">Reddit</a>' in html
    # no markers remain
    assert "\ue200" not in html
    assert "\ue201" not in html
    assert "\ue202" not in html
```

Step 2: Run test

Run: `pytest tests/test_apple_notes_content_types.py::test_renders_citations_from_real_conversation_structure -v`

Expected: PASS

Step 3: Commit test

```bash
git add tests/test_apple_notes_content_types.py
git commit -m "test: add e2e test for citation rendering"
```

---

## Task 7: Manual verification with real file

Step 1: Run the tool on the real JSON file

```bash
python -m chatgpt2applenotes "/Users/acolomba/Downloads/ChatGPT-Mac_Dictation_Features.json" --cc tmp/cc --dry-run
```

Step 2: Inspect output

```bash
cat tmp/cc/Mac_Dictation_Features.html | head -100
```

Look for:

- Citation markers replaced with `(<a href="...">Attribution</a>)`
- No garbled characters like `îˆ€citeîˆ‚`
- Links are clickable attributions

Step 3: Final commit (if any cleanup needed)

If all looks good, no commit needed. Otherwise fix and commit.

---

## Task 8: Final cleanup and squash

Step 1: Run full test suite

```bash
pytest tests/ -v
```

Expected: All tests pass

Step 2: Run linters

```bash
pre-commit run --all-files
```

Expected: All pass

Step 3: Review commits

```bash
git log --oneline main..HEAD
```

Consider squashing if there are many small commits.
