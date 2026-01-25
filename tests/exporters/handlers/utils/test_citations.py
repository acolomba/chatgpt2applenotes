"""tests for citation rendering utilities."""

from chatgpt2applenotes.exporters.handlers.utils.citations import render_citations


def test_replaces_citation_with_link() -> None:
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


def test_renders_multiple_sources() -> None:
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


def test_removes_marker_without_items() -> None:
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


def test_skips_whitespace_markers() -> None:
    """skips whitespace-only matched_text to preserve spaces."""
    html = "Hello world"
    metadata = {"content_references": [{"matched_text": " ", "items": []}]}
    result = render_citations(html, metadata)
    assert result == "Hello world"


def test_no_metadata_returns_unchanged() -> None:
    """returns unchanged HTML when no metadata."""
    html = "<div>content</div>"
    result = render_citations(html, None)
    assert result == html
