"""tests for progress module."""

from unittest.mock import MagicMock, patch

from rich.console import Console

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


def test_adjust_total_increases_total() -> None:
    """adjust_total increases the total count."""
    with patch("chatgpt2applenotes.progress.Progress") as mock_progress_class:
        mock_progress = MagicMock()
        mock_progress_class.return_value = mock_progress
        mock_progress.add_task.return_value = 0

        handler = ProgressHandler(show_progress=True)
        handler.start_discovery()
        handler.set_total(10)
        handler.adjust_total(5)

        # should update task total to 15
        mock_progress.update.assert_called()


def test_update_advances_progress_and_sets_title() -> None:
    """update advances progress by 1 and sets current title."""
    with patch("chatgpt2applenotes.progress.Progress") as mock_progress_class:
        mock_progress = MagicMock()
        mock_progress_class.return_value = mock_progress
        mock_progress.add_task.return_value = 0

        handler = ProgressHandler(show_progress=True)
        handler.start_discovery()
        handler.set_total(10)
        handler.update("Test Title")

        mock_progress.update.assert_called()


def test_log_error_prints_to_console() -> None:
    """log_error prints error message to console."""
    with patch.object(Console, "print") as mock_print:
        handler = ProgressHandler()
        handler.log_error("Test error")

        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "Test error" in call_args


def test_finish_prints_summary_when_not_quiet() -> None:
    """finish prints summary when quiet is False."""
    with patch.object(Console, "print") as mock_print:
        handler = ProgressHandler(quiet=False)
        handler.finish(processed=5, failed=2)

        mock_print.assert_called()


def test_finish_skips_summary_when_quiet() -> None:
    """finish skips summary when quiet is True."""
    with patch.object(Console, "print") as mock_print:
        handler = ProgressHandler(quiet=True)
        handler.finish(processed=5, failed=2)

        # should not print summary (only errors allowed)
        assert mock_print.call_count == 0


def test_log_info_prints_when_not_quiet_and_no_progress() -> None:
    """log_info prints when quiet=False and show_progress=False."""
    with patch.object(Console, "print") as mock_print:
        handler = ProgressHandler(quiet=False, show_progress=False)
        handler.log_info("Test info")

        mock_print.assert_called_once()


def test_log_info_skips_when_quiet() -> None:
    """log_info skips printing when quiet=True."""
    with patch.object(Console, "print") as mock_print:
        handler = ProgressHandler(quiet=True, show_progress=False)
        handler.log_info("Test info")

        mock_print.assert_not_called()


def test_log_info_skips_when_progress_enabled() -> None:
    """log_info skips printing when show_progress=True."""
    with patch.object(Console, "print") as mock_print:
        handler = ProgressHandler(quiet=False, show_progress=True)
        handler.log_info("Test info")

        mock_print.assert_not_called()
