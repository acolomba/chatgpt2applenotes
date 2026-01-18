"""tests for CLI argument parsing."""

import pytest

from chatgpt2applenotes import main


def test_cli_requires_source_argument() -> None:
    """CLI requires source argument."""
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 2  # argparse exits with 2 for missing args


def test_cli_accepts_source_only() -> None:
    """CLI accepts source as only positional argument, folder defaults to ChatGPT."""
    # this will fail because file doesn't exist, but parsing should succeed
    result = main(["nonexistent.json"])
    assert result == 2  # fatal error (file not found)


def test_cli_accepts_source_and_folder() -> None:
    """CLI accepts source and folder as positional arguments."""
    result = main(["nonexistent.json", "MyFolder"])
    assert result == 2  # fatal error (file not found)


def test_cli_accepts_dry_run_flag() -> None:
    """CLI accepts --dry-run flag."""
    result = main(["nonexistent.json", "--dry-run"])
    assert result == 2  # fatal error (file not found)


def test_cli_accepts_overwrite_flag() -> None:
    """CLI accepts --overwrite flag."""
    result = main(["nonexistent.json", "--overwrite"])
    assert result == 2


def test_cli_accepts_archive_deleted_flag() -> None:
    """CLI accepts --archive-deleted flag."""
    result = main(["nonexistent.json", "--archive-deleted"])
    assert result == 2


def test_cli_accepts_verbose_short_flag() -> None:
    """CLI accepts -v flag."""
    result = main(["nonexistent.json", "-v"])
    assert result == 2


def test_cli_accepts_verbose_long_flag() -> None:
    """CLI accepts --verbose flag."""
    result = main(["nonexistent.json", "--verbose"])
    assert result == 2


def test_cli_accepts_cc_flag() -> None:
    """CLI accepts --cc flag with directory argument."""
    result = main(["nonexistent.json", "--cc", "/tmp/cc-test"])
    assert result == 2  # fatal error (file not found, but arg parsing succeeded)


def test_cli_accepts_progress_flag() -> None:
    """CLI accepts --progress flag."""
    result = main(["nonexistent.json", "--progress"])
    assert result == 2  # fatal error (file not found, but arg parsing succeeded)


def test_cli_accepts_quiet_flag() -> None:
    """CLI accepts --quiet flag."""
    result = main(["nonexistent.json", "--quiet"])
    assert result == 2


def test_cli_accepts_quiet_short_flag() -> None:
    """CLI accepts -q flag."""
    result = main(["nonexistent.json", "-q"])
    assert result == 2


def test_cli_accepts_progress_and_quiet_together() -> None:
    """CLI accepts --progress and --quiet together."""
    result = main(["nonexistent.json", "--progress", "--quiet"])
    assert result == 2
