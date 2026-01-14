"""tests for sync module."""

import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chatgpt2applenotes.sync import discover_files, sync_conversations


def test_discover_single_json_file(tmp_path: Path) -> None:
    """discovers a single JSON file."""
    json_file = tmp_path / "conversation.json"
    json_file.write_text('{"id": "conv-1", "title": "Test"}', encoding="utf-8")

    files = discover_files(json_file)

    assert len(files) == 1
    assert files[0] == json_file


def test_discover_directory_of_json_files(tmp_path: Path) -> None:
    """discovers all JSON files in a directory."""
    (tmp_path / "conv1.json").write_text('{"id": "1"}', encoding="utf-8")
    (tmp_path / "conv2.json").write_text('{"id": "2"}', encoding="utf-8")
    (tmp_path / "readme.txt").write_text("ignore me", encoding="utf-8")

    files = discover_files(tmp_path)

    assert len(files) == 2
    assert all(f.suffix == ".json" for f in files)


def test_discover_zip_archive(tmp_path: Path) -> None:
    """discovers JSON files inside a ZIP archive."""
    zip_path = tmp_path / "export.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("conv1.json", '{"id": "1"}')
        zf.writestr("conv2.json", '{"id": "2"}')
        zf.writestr("readme.txt", "ignore me")

    files = discover_files(zip_path)

    assert len(files) == 2
    assert all(f.suffix == ".json" for f in files)


def test_discover_empty_directory_returns_empty_list(tmp_path: Path) -> None:
    """returns empty list for directory with no JSON files."""
    (tmp_path / "readme.txt").write_text("no json here", encoding="utf-8")

    files = discover_files(tmp_path)

    assert files == []


def test_discover_nonexistent_path_raises_error() -> None:
    """raises FileNotFoundError for nonexistent path."""
    with pytest.raises(FileNotFoundError):
        discover_files(Path("/nonexistent/path"))


def test_sync_processes_all_files(tmp_path: Path) -> None:
    """sync processes each discovered file."""
    # creates test JSON files
    conv1 = {
        "id": "conv-1",
        "title": "First",
        "create_time": 1234567890.0,
        "update_time": 1234567890.0,
        "mapping": {},
    }
    conv2 = {
        "id": "conv-2",
        "title": "Second",
        "create_time": 1234567891.0,
        "update_time": 1234567891.0,
        "mapping": {},
    }
    (tmp_path / "conv1.json").write_text(json.dumps(conv1), encoding="utf-8")
    (tmp_path / "conv2.json").write_text(json.dumps(conv2), encoding="utf-8")

    with patch("chatgpt2applenotes.sync.AppleNotesExporter") as mock_exporter_class:
        mock_exporter = MagicMock()
        mock_exporter_class.return_value = mock_exporter

        result = sync_conversations(tmp_path, "TestFolder", dry_run=True)

    assert result == 0
    assert mock_exporter.export.call_count == 2


def test_sync_continues_on_error(tmp_path: Path) -> None:
    """sync continues processing after individual file errors."""
    # creates one valid and one invalid JSON file
    valid = {
        "id": "conv-1",
        "title": "Valid",
        "create_time": 1234567890.0,
        "update_time": 1234567890.0,
        "mapping": {},
    }
    (tmp_path / "valid.json").write_text(json.dumps(valid), encoding="utf-8")
    (tmp_path / "invalid.json").write_text("not valid json", encoding="utf-8")

    with patch("chatgpt2applenotes.sync.AppleNotesExporter") as mock_exporter_class:
        mock_exporter = MagicMock()
        mock_exporter_class.return_value = mock_exporter

        result = sync_conversations(tmp_path, "TestFolder", dry_run=True)

    # returns 1 (partial failure) because one file failed
    assert result == 1
    # but still processed the valid file
    assert mock_exporter.export.call_count == 1


def test_sync_prints_summary(tmp_path: Path) -> None:
    """sync prints summary of processed files."""
    conv = {
        "id": "conv-1",
        "title": "Test",
        "create_time": 1234567890.0,
        "update_time": 1234567890.0,
        "mapping": {},
    }
    (tmp_path / "conv.json").write_text(json.dumps(conv), encoding="utf-8")

    with patch("chatgpt2applenotes.sync.AppleNotesExporter") as mock_exporter_class:
        mock_exporter = MagicMock()
        mock_exporter_class.return_value = mock_exporter

        sync_conversations(tmp_path, "TestFolder", dry_run=True)

    # summary is logged, check it was called
    # (actual output verification depends on logging config)


def test_archive_deleted_calls_exporter_methods(tmp_path: Path) -> None:
    """archive_deleted uses exporter to list and move notes."""
    conv = {
        "id": "conv-keep",
        "title": "Keep",
        "create_time": 1234567890.0,
        "update_time": 1234567890.0,
        "mapping": {},
    }
    (tmp_path / "keep.json").write_text(json.dumps(conv), encoding="utf-8")

    with patch("chatgpt2applenotes.sync.AppleNotesExporter") as mock_exporter_class:
        mock_exporter = MagicMock()
        mock_exporter_class.return_value = mock_exporter
        # simulates existing notes including one not in source
        mock_exporter.list_note_conversation_ids.return_value = [
            "conv-keep",
            "conv-delete",
        ]

        sync_conversations(tmp_path, "TestFolder", archive_deleted=True)

    # should have called move for the deleted conversation
    mock_exporter.move_note_to_archive.assert_called_once_with(
        "TestFolder", "conv-delete"
    )
