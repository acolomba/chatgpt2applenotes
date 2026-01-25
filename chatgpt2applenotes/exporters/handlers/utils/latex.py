"""LaTeX protection utilities for markdown processing."""

import html
import re

LATEX_PATTERN = re.compile(
    r"(\$\$[\s\S]+?\$\$)|(\$[^\$\n]+?\$)|(\\\[[\s\S]+?\\\])|(\\\([\s\S]+?\\\))",
    re.MULTILINE,
)


def protect_latex(text: str) -> tuple[str, list[str]]:
    """
    replaces LaTeX with placeholders to protect from markdown processing.

    Args:
        text: input text containing LaTeX

    Returns:
        tuple of (protected text, list of LaTeX matches)
    """
    matches: list[str] = []

    def replacer(match: re.Match[str]) -> str:
        matches.append(match.group(0))
        return f"╣{len(matches) - 1}╣"

    return LATEX_PATTERN.sub(replacer, text), matches


def restore_latex(text: str, matches: list[str]) -> str:
    """
    restores LaTeX from placeholders with HTML escaping.

    Args:
        text: text with placeholders
        matches: list of original LaTeX strings

    Returns:
        text with LaTeX restored (HTML-escaped)
    """
    for i, latex in enumerate(matches):
        text = text.replace(f"╣{i}╣", html.escape(latex))
    return text
