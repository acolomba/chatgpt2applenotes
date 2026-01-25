"""tests for markdown to Apple Notes HTML conversion."""

from chatgpt2applenotes.exporters.handlers.utils.markdown import markdown_to_html


def test_converts_bold() -> None:
    """converts **bold** to <b>."""
    result = markdown_to_html("This is **bold** text")
    assert "<b>bold</b>" in result


def test_converts_italic() -> None:
    """converts *italic* to <i>."""
    result = markdown_to_html("This is *italic* text")
    assert "<i>italic</i>" in result


def test_converts_paragraphs_to_divs() -> None:
    """converts paragraphs to divs for Apple Notes."""
    result = markdown_to_html("First paragraph\n\nSecond paragraph")
    assert "<div>" in result
    assert "</div>" in result
    assert "<p>" not in result


def test_converts_inline_code() -> None:
    """converts inline code to <tt>."""
    result = markdown_to_html("Use `code` here")
    assert "<tt>code</tt>" in result


def test_converts_code_blocks() -> None:
    """converts code blocks to <pre>."""
    result = markdown_to_html("```\ncode block\n```")
    assert "<pre>" in result
    assert "</pre>" in result


def test_preserves_latex() -> None:
    """preserves LaTeX without markdown processing."""
    result = markdown_to_html("Formula $a_1$ here")
    assert "$a_1$" in result
    # underscore should not become <i>
    assert "<i>1</i>" not in result


def test_converts_unordered_lists() -> None:
    """converts unordered lists with bullet markers."""
    result = markdown_to_html("- item 1\n- item 2")
    # should use div with bullet, not native <ul>/<li>
    assert "<ul>" not in result


def test_converts_ordered_lists() -> None:
    """converts ordered lists with number markers."""
    result = markdown_to_html("1. first\n2. second")
    # should use div with number, not native <ol>/<li>
    assert "<ol>" not in result
    assert "1." in result or "1.\t" in result


def test_renders_tables() -> None:
    """renders markdown tables."""
    md = "| A | B |\n|---|---|\n| 1 | 2 |"
    result = markdown_to_html(md)
    assert "<table>" in result


def test_escapes_html() -> None:
    """escapes HTML in input."""
    result = markdown_to_html("<script>alert('xss')</script>")
    assert "<script>" not in result
    assert "&lt;script&gt;" in result
