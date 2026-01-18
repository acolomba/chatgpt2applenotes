"""tests for progress module."""

from unittest.mock import MagicMock, patch

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


def test_start_discovery_shows_spinner_when_progress_enabled() -> None:
    """start_discovery shows spinner when show_progress is True."""
    with patch("chatgpt2applenotes.progress.Progress") as mock_progress_class:
        mock_progress = MagicMock()
        mock_progress_class.return_value = mock_progress
        mock_progress.add_task.return_value = 0

        handler = ProgressHandler(show_progress=True)
        handler.start_discovery()

        mock_progress.start.assert_called_once()
        mock_progress.add_task.assert_called_once()


def test_start_discovery_does_nothing_when_progress_disabled() -> None:
    """start_discovery does nothing when show_progress is False."""
    with patch("chatgpt2applenotes.progress.Progress") as mock_progress_class:
        handler = ProgressHandler(show_progress=False)
        handler.start_discovery()

        mock_progress_class.assert_not_called()


def test_set_total_switches_to_determinate_progress() -> None:
    """set_total switches from spinner to determinate progress bar."""
    with patch("chatgpt2applenotes.progress.Progress") as mock_progress_class:
        mock_progress = MagicMock()
        mock_progress_class.return_value = mock_progress
        mock_progress.add_task.return_value = 0

        handler = ProgressHandler(show_progress=True)
        handler.start_discovery()
        handler.set_total(10)

        # should stop spinner and start new progress bar
        assert mock_progress.stop.call_count >= 1


def test_set_total_does_nothing_when_progress_disabled() -> None:
    """set_total does nothing when show_progress is False."""
    handler = ProgressHandler(show_progress=False)
    handler.set_total(10)  # should not raise
