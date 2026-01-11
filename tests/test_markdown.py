"""tests markdown rendering functionality."""

from chatgpt2applenotes.core.markdown_ast import render_markdown_to_html


def test_render_simple_text() -> None:
    """tests simple text rendering to HTML."""
    markdown = "Hello world"
    html = render_markdown_to_html(markdown)
    assert html == "<p>Hello world</p>"


def test_render_bold() -> None:
    """tests bold text rendering to HTML."""
    markdown = "**bold text**"
    html = render_markdown_to_html(markdown)
    assert html == "<p><strong>bold text</strong></p>"


def test_render_code_block() -> None:
    """tests code block rendering to HTML with language class."""
    markdown = "```python\nprint('hello')\n```"
    html = render_markdown_to_html(markdown)
    assert '<code class="language-python">' in html
    assert "print('hello')" in html
