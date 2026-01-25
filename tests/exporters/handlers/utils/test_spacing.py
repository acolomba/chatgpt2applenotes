"""tests for block spacing utilities."""

from chatgpt2applenotes.exporters.handlers.utils.spacing import add_block_spacing


def test_adds_spacing_between_divs() -> None:
    """adds spacing between adjacent div elements."""
    html = "</div><div>"
    result = add_block_spacing(html)
    assert "<div><br></div>" in result


def test_adds_spacing_between_different_blocks() -> None:
    """adds spacing between different block elements."""
    html = "</ul><div>"
    result = add_block_spacing(html)
    assert "<div><br></div>" in result


def test_handles_consecutive_blocks() -> None:
    """handles multiple consecutive block elements."""
    html = "</div><div></div><div>"
    result = add_block_spacing(html)
    assert result.count("<div><br></div>") == 2


def test_cleans_empty_divs_in_lists() -> None:
    """removes empty divs from loose list rendering."""
    html = "<li><div></div>content</li>"
    result = add_block_spacing(html)
    assert "<li>\ncontent</li>" in result


def test_no_change_for_inline_content() -> None:
    """does not modify inline content."""
    html = "<span>hello</span><span>world</span>"
    result = add_block_spacing(html)
    assert result == html
