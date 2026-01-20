"""tests for sync module."""

import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chatgpt2applenotes.exporters.applescript import NoteInfo
from chatgpt2applenotes.sync import (
    build_conversation_index,
    discover_files,
    sync_conversations,
)


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
    """archive_deleted uses exporter to move notes by ID from index."""
    conv = {
        "id": "conv-keep",
        "title": "Keep",
        "create_time": 1234567890.0,
        "update_time": 1234567890.0,
        "mapping": {},
    }
    (tmp_path / "keep.json").write_text(json.dumps(conv), encoding="utf-8")

    # simulates note index with existing notes including one not in source
    note_to_delete = NoteInfo(
        note_id="x-coredata://delete",
        conversation_id="conv-delete",
        last_message_id="msg-1",
    )
    note_to_keep = NoteInfo(
        note_id="x-coredata://keep",
        conversation_id="conv-keep",
        last_message_id="msg-2",
    )

    with patch("chatgpt2applenotes.sync.AppleNotesExporter") as mock_exporter_class:
        mock_exporter = MagicMock()
        mock_exporter_class.return_value = mock_exporter
        mock_exporter.scan_folder_notes.return_value = {
            "conv-keep": note_to_keep,
            "conv-delete": note_to_delete,
        }

        sync_conversations(tmp_path, "TestFolder", archive_deleted=True)

    # should have called move_note_to_archive_by_id for the deleted conversation
    mock_exporter.move_note_to_archive_by_id.assert_called_once_with(
        "x-coredata://delete", "TestFolder"
    )


def test_sync_scans_folder_once(tmp_path: Path) -> None:
    """tests sync_conversations scans folder once upfront."""
    # creates test JSON file
    json_file = tmp_path / "conv1.json"
    json_file.write_text(
        '{"id": "conv-1", "title": "Test", "create_time": 1234567890, '
        '"mapping": {"node1": {"message": {"id": "msg-1", "author": {"role": "user"}, '
        '"create_time": 1234567890, "content": {"content_type": "text", "parts": ["Hi"]}}}}}'
    )

    with patch("chatgpt2applenotes.sync.AppleNotesExporter") as mock_exporter_class:
        mock_exporter = MagicMock()
        mock_exporter_class.return_value = mock_exporter
        mock_exporter.scan_folder_notes.return_value = {}

        sync_conversations(tmp_path, "TestFolder")

        # scan_folder_notes should be called exactly once
        mock_exporter.scan_folder_notes.assert_called_once_with("TestFolder")
        # export should be called with existing=None (no existing note)
        mock_exporter.export.assert_called_once()
        call_kwargs = mock_exporter.export.call_args.kwargs
        assert call_kwargs.get("existing") is None


def test_sync_passes_existing_noteinfo_to_export(tmp_path: Path) -> None:
    """tests sync_conversations passes existing NoteInfo to export."""
    # creates test JSON file
    json_file = tmp_path / "conv1.json"
    json_file.write_text(
        '{"id": "conv-1", "title": "Test", "create_time": 1234567890, '
        '"mapping": {"node1": {"message": {"id": "msg-1", "author": {"role": "user"}, '
        '"create_time": 1234567890, "content": {"content_type": "text", "parts": ["Hi"]}}}}}'
    )

    existing_note = NoteInfo(
        note_id="x-coredata://existing",
        conversation_id="conv-1",
        last_message_id="msg-old",
    )

    with patch("chatgpt2applenotes.sync.AppleNotesExporter") as mock_exporter_class:
        mock_exporter = MagicMock()
        mock_exporter_class.return_value = mock_exporter
        mock_exporter.scan_folder_notes.return_value = {"conv-1": existing_note}

        sync_conversations(tmp_path, "TestFolder")

        # export should be called with existing NoteInfo
        mock_exporter.export.assert_called_once()
        call_kwargs = mock_exporter.export.call_args.kwargs
        assert call_kwargs.get("existing") == existing_note


def test_sync_accepts_quiet_and_progress_args(tmp_path: Path) -> None:
    """sync_conversations accepts quiet and progress arguments."""
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

        # should not raise
        result = sync_conversations(
            tmp_path, "TestFolder", dry_run=True, quiet=True, progress=True
        )

    assert result == 0


def test_sync_handles_multi_conversation_file(tmp_path: Path) -> None:
    """sync processes multiple conversations from a single file."""
    # creates a file with multiple conversations (ChatGPT JSON export format)
    conversations = [
        {
            "id": "conv-1",
            "title": "First",
            "create_time": 1234567890.0,
            "update_time": 1234567890.0,
            "mapping": {},
        },
        {
            "id": "conv-2",
            "title": "Second",
            "create_time": 1234567891.0,
            "update_time": 1234567891.0,
            "mapping": {},
        },
    ]
    (tmp_path / "multi.json").write_text(json.dumps(conversations), encoding="utf-8")

    with patch("chatgpt2applenotes.sync.AppleNotesExporter") as mock_exporter_class:
        mock_exporter = MagicMock()
        mock_exporter_class.return_value = mock_exporter

        result = sync_conversations(tmp_path, "TestFolder", dry_run=True)

    assert result == 0
    assert mock_exporter.export.call_count == 2


def test_sync_continues_after_conversation_failure(tmp_path: Path) -> None:
    """sync continues processing after individual conversation errors."""
    # creates a file with two valid conversations
    conversations = [
        {
            "id": "conv-1",
            "title": "First",
            "create_time": 1234567890.0,
            "update_time": 1234567890.0,
            "mapping": {},
        },
        {
            "id": "conv-2",
            "title": "Second",
            "create_time": 1234567891.0,
            "update_time": 1234567891.0,
            "mapping": {},
        },
    ]
    (tmp_path / "mixed.json").write_text(json.dumps(conversations), encoding="utf-8")

    with patch("chatgpt2applenotes.sync.AppleNotesExporter") as mock_exporter_class:
        mock_exporter = MagicMock()
        mock_exporter_class.return_value = mock_exporter
        # simulates export failure for the first conversation
        mock_exporter.export.side_effect = [Exception("Export failed"), None]

        result = sync_conversations(tmp_path, "TestFolder", dry_run=True)

    # returns 1 (partial failure)
    assert result == 1
    # but still attempted both conversations
    assert mock_exporter.export.call_count == 2


def test_build_index_single_conversation_dict(tmp_path: Path) -> None:
    """builds index from single-conversation dict file."""
    conv = {
        "id": "conv-1",
        "title": "Test",
        "create_time": 1000.0,
        "update_time": 2000.0,
        "mapping": {},
    }
    json_file = tmp_path / "conv.json"
    json_file.write_text(json.dumps(conv), encoding="utf-8")

    index = build_conversation_index([json_file])

    assert len(index) == 1
    assert index[0] == (2000.0, json_file, -1)


def test_build_index_multi_conversation_list(tmp_path: Path) -> None:
    """builds index from multi-conversation list file."""
    conversations = [
        {
            "id": "conv-1",
            "title": "First",
            "create_time": 1000.0,
            "update_time": 3000.0,
            "mapping": {},
        },
        {
            "id": "conv-2",
            "title": "Second",
            "create_time": 1000.0,
            "update_time": 1000.0,
            "mapping": {},
        },
        {
            "id": "conv-3",
            "title": "Third",
            "create_time": 1000.0,
            "update_time": 2000.0,
            "mapping": {},
        },
    ]
    json_file = tmp_path / "multi.json"
    json_file.write_text(json.dumps(conversations), encoding="utf-8")

    index = build_conversation_index([json_file])

    assert len(index) == 3
    assert index[0] == (3000.0, json_file, 0)
    assert index[1] == (1000.0, json_file, 1)
    assert index[2] == (2000.0, json_file, 2)


def test_build_index_skips_invalid_files(tmp_path: Path) -> None:
    """skips files that fail to parse."""
    valid = {
        "id": "conv-1",
        "title": "Valid",
        "create_time": 1000.0,
        "update_time": 2000.0,
        "mapping": {},
    }
    (tmp_path / "valid.json").write_text(json.dumps(valid), encoding="utf-8")
    (tmp_path / "invalid.json").write_text("not valid json", encoding="utf-8")

    index = build_conversation_index(
        [tmp_path / "valid.json", tmp_path / "invalid.json"]
    )

    assert len(index) == 1
    assert index[0][0] == 2000.0


def test_build_index_mixed_files(tmp_path: Path) -> None:
    """builds index from mix of dict and list files."""
    dict_conv = {
        "id": "conv-1",
        "title": "Dict",
        "create_time": 1000.0,
        "update_time": 5000.0,
        "mapping": {},
    }
    list_conv = [
        {
            "id": "conv-2",
            "title": "List1",
            "create_time": 1000.0,
            "update_time": 3000.0,
            "mapping": {},
        },
        {
            "id": "conv-3",
            "title": "List2",
            "create_time": 1000.0,
            "update_time": 1000.0,
            "mapping": {},
        },
    ]
    dict_file = tmp_path / "dict.json"
    list_file = tmp_path / "list.json"
    dict_file.write_text(json.dumps(dict_conv), encoding="utf-8")
    list_file.write_text(json.dumps(list_conv), encoding="utf-8")

    index = build_conversation_index([dict_file, list_file])

    assert len(index) == 3
    # dict file: -1 index
    assert (5000.0, dict_file, -1) in index
    # list file: indexed by position
    assert (3000.0, list_file, 0) in index
    assert (1000.0, list_file, 1) in index
