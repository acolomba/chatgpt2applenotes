"""markdown to Apple Notes HTML conversion."""

import html as html_lib
from typing import Any, cast

from markdown_it import MarkdownIt

from chatgpt2applenotes.exporters.handlers.utils.latex import (
    protect_latex,
    restore_latex,
)
from chatgpt2applenotes.exporters.handlers.utils.spacing import add_block_spacing


def markdown_to_html(text: str) -> str:
    """
    converts markdown to Apple Notes-compatible HTML.

    Args:
        text: markdown text

    Returns:
        Apple Notes-compatible HTML
    """
    protected_text, latex_matches = protect_latex(text)

    md = MarkdownIt()
    md.enable("table")
    md.disable("html_inline")
    md.disable("html_block")

    renderer: Any = md.renderer
    original_render_token = renderer.renderToken

    # tracks list state for numbered lists
    list_state: list[tuple[str, int]] = []

    def _handle_list_token(tag: str, nesting: int) -> str:
        """handles ul/ol/li tokens for Apple Notes list rendering."""
        if tag in ("ul", "ol"):
            if nesting == 1:
                list_state.append((tag, 0))
            elif list_state:
                list_state.pop()
            return ""
        # li tag
        if nesting != 1:
            return "</div>\n"
        # opening li
        if list_state and list_state[-1][0] == "ol":
            list_type, counter = list_state[-1]
            list_state[-1] = (list_type, counter + 1)
            return f"<div>{counter + 1}.\t"
        return "<div>\u2022\t"

    def custom_render_token(tokens: Any, idx: int, options: Any, env: Any) -> str:
        """custom token renderer for Apple Notes compatibility."""
        token = tokens[idx]

        if token.tag in ("ul", "ol", "li"):
            return _handle_list_token(token.tag, token.nesting)

        tag_map = {"p": "div", "strong": "b", "em": "i", "code": "tt"}
        if token.tag in tag_map:
            token.tag = tag_map[token.tag]

        return cast(str, original_render_token(tokens, idx, options, env))

    renderer.renderToken = custom_render_token

    def render_code_block(tokens: Any, idx: int, _options: Any, _env: Any) -> str:
        token = tokens[idx]
        escaped = html_lib.escape(token.content)
        return f"<pre>{escaped}</pre>\n"

    renderer.rules["code_block"] = render_code_block
    renderer.rules["fence"] = render_code_block

    def render_code_inline(tokens: Any, idx: int, _options: Any, _env: Any) -> str:
        token = tokens[idx]
        escaped = html_lib.escape(token.content)
        return f"<tt>{escaped}</tt>"

    renderer.rules["code_inline"] = render_code_inline

    def render_image(tokens: Any, idx: int, _options: Any, _env: Any) -> str:
        token = tokens[idx]
        src = token.attrGet("src") or ""
        escaped_src = html_lib.escape(src)
        return f'<div><img src="{escaped_src}" style="max-width: 100%; max-height: 100%;"></div>\n'

    renderer.rules["image"] = render_image

    result = cast(str, md.render(protected_text))
    result = restore_latex(result, latex_matches) if latex_matches else result

    return add_block_spacing(result)
