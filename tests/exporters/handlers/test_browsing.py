"""tests for browsing content handlers."""

# pylint: disable=redefined-outer-name

from typing import Any

import pytest

from chatgpt2applenotes.exporters.handlers import RenderContext
from chatgpt2applenotes.exporters.handlers.browsing import (
    SonicWebpageHandler,
    TetherBrowsingDisplayHandler,
    TetherQuoteHandler,
)


@pytest.fixture
def ctx() -> RenderContext:
    """provides a render context for tests."""
    return RenderContext()


class TestTetherQuoteHandler:
    """tests for TetherQuoteHandler."""

    def test_renders_as_blockquote(self, ctx: RenderContext) -> None:
        """renders quoted text in blockquote."""
        handler = TetherQuoteHandler()
        content = {
            "content_type": "tether_quote",
            "url": "https://example.com",
            "text": "This is quoted content",
        }
        result = handler.render(content, None, ctx)
        assert "<blockquote>" in result
        assert "This is quoted content" in result

    def test_escapes_html(self, ctx: RenderContext) -> None:
        """escapes HTML in quoted text."""
        handler = TetherQuoteHandler()
        content = {
            "content_type": "tether_quote",
            "url": "https://example.com",
            "text": "<script>bad</script>",
        }
        result = handler.render(content, None, ctx)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_handles_missing_text(self, ctx: RenderContext) -> None:
        """handles missing text field gracefully."""
        handler = TetherQuoteHandler()
        content = {
            "content_type": "tether_quote",
            "url": "https://example.com",
        }
        result = handler.render(content, None, ctx)
        assert "<blockquote>" in result
        assert "</blockquote>" in result


class TestTetherBrowsingDisplayHandler:
    """tests for TetherBrowsingDisplayHandler."""

    def test_renders_links_from_metadata(self, ctx: RenderContext) -> None:
        """renders links from cite_metadata."""
        handler = TetherBrowsingDisplayHandler()
        content = {"content_type": "tether_browsing_display", "result": "text"}
        metadata = {
            "_cite_metadata": {
                "metadata_list": [
                    {"url": "https://a.com", "title": "Site A"},
                    {"url": "https://b.com", "title": "Site B"},
                ]
            }
        }
        result = handler.render(content, metadata, ctx)
        assert "https://a.com" in result
        assert "Site A" in result
        assert "https://b.com" in result

    def test_handles_missing_metadata(self, ctx: RenderContext) -> None:
        """handles missing cite_metadata gracefully."""
        handler = TetherBrowsingDisplayHandler()
        content = {"content_type": "tether_browsing_display", "result": "text"}
        result = handler.render(content, None, ctx)
        # should return empty or minimal content
        assert result is not None

    def test_handles_empty_metadata_list(self, ctx: RenderContext) -> None:
        """handles empty metadata_list gracefully."""
        handler = TetherBrowsingDisplayHandler()
        content = {"content_type": "tether_browsing_display", "result": "text"}
        metadata: dict[str, Any] = {"_cite_metadata": {"metadata_list": []}}
        result = handler.render(content, metadata, ctx)
        assert result == ""

    def test_uses_url_as_title_fallback(self, ctx: RenderContext) -> None:
        """uses URL as title when title is missing."""
        handler = TetherBrowsingDisplayHandler()
        content = {"content_type": "tether_browsing_display", "result": "text"}
        metadata = {
            "_cite_metadata": {
                "metadata_list": [
                    {"url": "https://example.com"},
                ]
            }
        }
        result = handler.render(content, metadata, ctx)
        assert "https://example.com" in result
        # URL should appear in both href and link text
        assert result.count("https://example.com") >= 2


class TestSonicWebpageHandler:
    """tests for SonicWebpageHandler."""

    def test_renders_title_as_link(self, ctx: RenderContext) -> None:
        """renders title as link to URL."""
        handler = SonicWebpageHandler()
        content = {
            "content_type": "sonic_webpage",
            "url": "https://example.com/page",
            "title": "Example Page",
        }
        result = handler.render(content, None, ctx)
        assert '<a href="https://example.com/page"' in result
        assert "Example Page" in result

    def test_escapes_html_in_title(self, ctx: RenderContext) -> None:
        """escapes HTML in title."""
        handler = SonicWebpageHandler()
        content = {
            "content_type": "sonic_webpage",
            "url": "https://example.com",
            "title": "<script>bad</script>",
        }
        result = handler.render(content, None, ctx)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_handles_missing_title(self, ctx: RenderContext) -> None:
        """handles missing title gracefully."""
        handler = SonicWebpageHandler()
        content = {
            "content_type": "sonic_webpage",
            "url": "https://example.com",
        }
        result = handler.render(content, None, ctx)
        assert "https://example.com" in result

    def test_escapes_html_in_url(self, ctx: RenderContext) -> None:
        """escapes HTML in URL."""
        handler = SonicWebpageHandler()
        content = {
            "content_type": "sonic_webpage",
            "url": 'https://example.com?q=<script>"test"</script>',
            "title": "Test",
        }
        result = handler.render(content, None, ctx)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
