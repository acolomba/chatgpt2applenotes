"""tests for LaTeX protection utilities."""

from chatgpt2applenotes.exporters.handlers.utils.latex import (
    protect_latex,
    restore_latex,
)


def test_protect_latex_inline() -> None:
    """protects inline LaTeX $...$ from markdown processing."""
    text = "The formula $E=mc^2$ is famous"
    protected, matches = protect_latex(text)
    assert "$E=mc^2$" not in protected
    assert len(matches) == 1
    assert matches[0] == "$E=mc^2$"


def test_protect_latex_display() -> None:
    """protects display LaTeX $$...$$ from markdown processing."""
    text = "Display: $$\\int_0^1 x^2 dx$$"
    protected, matches = protect_latex(text)
    assert "$$" not in protected
    assert len(matches) == 1


def test_protect_latex_brackets() -> None:
    """protects \\[...\\] and \\(...\\) LaTeX from markdown processing."""
    text = "Inline \\(a+b\\) and display \\[x^2\\]"
    protected, matches = protect_latex(text)
    assert "\\(" not in protected
    assert "\\[" not in protected
    assert len(matches) == 2


def test_restore_latex() -> None:
    """restores LaTeX from placeholders with HTML escaping."""
    matches = ["$E=mc^2$"]
    # note: index in placeholder is 0-based in actual implementation
    text_with_placeholder = "The formula ╣0╣ is famous"
    restored = restore_latex(text_with_placeholder, matches)
    assert "$E=mc^2$" in restored


def test_protect_and_restore_roundtrip() -> None:
    """protects and restores LaTeX correctly."""
    original = "Variables $a_1$ and $b_2$ are defined."
    protected, matches = protect_latex(original)
    restored = restore_latex(protected, matches)
    assert "$a_1$" in restored
    assert "$b_2$" in restored


def test_no_latex_returns_empty_matches() -> None:
    """text without LaTeX returns empty matches list."""
    text = "No math here"
    protected, matches = protect_latex(text)
    assert protected == text
    assert not matches
