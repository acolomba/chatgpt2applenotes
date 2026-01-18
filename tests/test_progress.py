"""tests for progress module."""

from chatgpt2applenotes.progress import ProgressHandler


def test_progress_handler_init_defaults() -> None:
    """ProgressHandler initializes with default values."""
    handler = ProgressHandler()

    assert handler.quiet is False
    assert handler.show_progress is False


def test_progress_handler_init_with_flags() -> None:
    """ProgressHandler accepts quiet and show_progress flags."""
    handler = ProgressHandler(quiet=True, show_progress=True)

    assert handler.quiet is True
    assert handler.show_progress is True


def test_progress_handler_context_manager() -> None:
    """ProgressHandler works as context manager."""
    with ProgressHandler() as handler:
        assert handler is not None
