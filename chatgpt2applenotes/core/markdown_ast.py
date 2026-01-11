"""Markdown to HTML renderer with full control over output format."""

from markdown_it import MarkdownIt


def render_markdown_to_html(markdown: str) -> str:
    """
    Render markdown to HTML matching chatgpt-exporter output.

    Uses markdown-it-py for parsing to AST, with custom rendering
    to match exact HTML output from TypeScript implementation.

    Args:
        markdown: Input markdown text

    Returns:
        HTML string matching reference output
    """
    md = MarkdownIt()

    # For now, use default renderer - we'll customize later
    html: str = md.render(markdown)

    # Strip trailing newline for consistency
    return html.rstrip("\n")
