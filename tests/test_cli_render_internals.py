"""tests for --render-internals CLI flag."""

from pathlib import Path

from chatgpt2applenotes import main


def test_render_internals_flag_accepted() -> None:
    """--render-internals flag is accepted by CLI."""
    # uses nonexistent file (will fail with exit code 2 for file not found)
    # but this verifies the flag is accepted and not rejected as unknown
    result = main(["nonexistent.json", "--render-internals"])
    assert result == 2  # fatal error (file not found, but arg parsing succeeded)


def test_render_internals_flag_with_dry_run(tmp_path: Path) -> None:
    """--render-internals flag works with --dry-run."""
    # creates a minimal JSON file
    json_file = tmp_path / "test.json"
    json_file.write_text('{"id": "1", "title": "T", "mapping": {}}')

    result = main([str(json_file), "--render-internals", "--dry-run"])
    # should succeed (or return 0 for empty conversation) since dry-run
    # skips Apple Notes interaction
    assert result in (0, 1)  # 0 = success, 1 = partial failure is acceptable
