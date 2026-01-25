"""block spacing utilities for Apple Notes HTML."""

import re


def add_block_spacing(html: str) -> str:
    """
    adds <div><br></div> between adjacent block elements at top level.

    Args:
        html: input HTML

    Returns:
        HTML with spacing added between block elements
    """
    # cleans up empty divs from markdown-it's loose list rendering
    html = re.sub(
        r"(<(?:li|blockquote)[^>]*>)\s*<div>(?:<br\s*/?>|\s)*</div>\s*",
        r"\1\n",
        html,
        flags=re.IGNORECASE,
    )

    # uses a unique marker to prevent infinite loops
    spacer_marker = "\x00SPACER\x00"

    # block element patterns (closing tag followed by opening tag)
    block_pattern = re.compile(
        r"(</(?:div|ul|ol|blockquote|pre|table|h[1-6])>)"
        r"(\s*)"
        r"(<(?:div|ul|ol|blockquote|pre|table|h[1-6])(?:\s|>))",
        re.IGNORECASE,
    )

    def add_spacer(match: re.Match[str]) -> str:
        return f"{match.group(1)}\n{spacer_marker}\n{match.group(3)}"

    # repeatedly applies until no more changes (handles consecutive blocks)
    prev = ""
    while prev != html:
        prev = html
        html = block_pattern.sub(add_spacer, html)

    # replaces markers with actual spacers
    return html.replace(spacer_marker, "<div><br></div>")
