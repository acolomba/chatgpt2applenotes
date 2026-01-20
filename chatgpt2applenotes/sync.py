"""Sync module for batch processing conversations."""

import json
import tempfile
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Optional

import ijson

from chatgpt2applenotes.core.parser import process_conversation
from chatgpt2applenotes.exporters.apple_notes import AppleNotesExporter
from chatgpt2applenotes.exporters.applescript import NoteInfo
from chatgpt2applenotes.progress import ProgressHandler


def discover_files(source: Path) -> list[Path]:
    """
    discovers JSON files from source path.

    Args:
        source: path to JSON file, directory, or ZIP archive

    Returns:
        list of paths to JSON files

    Raises:
        FileNotFoundError: if source doesn't exist
    """
    if not source.exists():
        raise FileNotFoundError(f"Source not found: {source}")

    if source.is_file():
        if source.suffix == ".zip":
            return _extract_zip(source)
        if source.suffix == ".json":
            return [source]
        return []

    if source.is_dir():
        return sorted(source.glob("*.json"))

    return []


def _extract_zip(zip_path: Path) -> list[Path]:
    """extracts JSON files from ZIP archive to temp directory."""
    # note: temp directory is cleaned up when sync loop implementation is complete
    temp_dir = Path(tempfile.mkdtemp(prefix="chatgpt2applenotes_"))
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if name.endswith(".json"):
                # extracts to temp_dir using only the filename, preventing path traversal
                source_info = zf.getinfo(name)
                safe_name = Path(name).name
                target_path = temp_dir / safe_name
                target_path.write_bytes(zf.read(source_info))

    return sorted(temp_dir.glob("*.json"))


def build_conversation_index(files: list[Path]) -> list[tuple[float, Path, int]]:
    """
    stream-parses files to build index of (update_time, path, index) tuples.

    Args:
        files: list of JSON file paths to index

    Returns:
        list of (update_time, path, index) tuples where index is -1 for dict
        files, >= 0 for list files
    """
    index: list[tuple[float, Path, int]] = []

    for file_path in files:
        try:
            with open(file_path, "rb") as f:
                # peeks first non-whitespace char
                first_char = _peek_first_char(f)
                f.seek(0)

                if first_char == ord("{"):
                    # single conversation dict
                    update_time = _extract_update_time_from_dict(f)
                    if update_time is not None:
                        index.append((update_time, file_path, -1))
                elif first_char == ord("["):
                    # list of conversations
                    for i, update_time in _extract_update_times_from_list(f):
                        index.append((update_time, file_path, i))
        except Exception:
            # skips files that fail to parse
            pass

    return index


def _peek_first_char(f: Any) -> int:
    """returns first non-whitespace byte from file."""
    while True:
        char = f.read(1)
        if not char:
            return 0
        if not char.isspace():
            return int(char[0])


def _extract_update_time_from_dict(f: Any) -> Optional[float]:
    """extracts update_time from a single conversation dict using streaming."""
    parser = ijson.parse(f)
    for prefix, event, value in parser:
        if prefix == "update_time" and event == "number":
            return float(value)
    return None


def _extract_update_times_from_list(f: Any) -> Iterator[tuple[int, float]]:
    """
    yields (index, update_time) tuples from a list of conversations using streaming.

    tracks array position via start_map events to preserve correct indices when
    conversations lack update_time.
    """
    parser = ijson.parse(f)
    current_index = -1
    for prefix, event, value in parser:
        if prefix == "item" and event == "start_map":
            current_index += 1
        elif prefix == "item.update_time" and event == "number":
            yield (current_index, float(value))


def sync_conversations(
    source: Path,
    folder: str,
    dry_run: bool = False,
    overwrite: bool = False,
    archive_deleted: bool = False,
    cc_dir: Optional[Path] = None,
    quiet: bool = False,
    progress: bool = False,
) -> int:
    """
    syncs conversations from source to Apple Notes.

    Args:
        source: path to JSON file, directory, or ZIP archive
        folder: Apple Notes folder name
        dry_run: if True, don't write to Apple Notes
        overwrite: if True, replace notes instead of appending
        archive_deleted: if True, move orphaned notes to Archive
        cc_dir: optional directory to save copies of generated HTML
        quiet: if True, suppress non-error output
        progress: if True, show progress bar

    Returns:
        exit code (0 success, 1 partial failure, 2 fatal error)
    """
    with ProgressHandler(quiet=quiet, show_progress=progress) as handler:
        handler.start_discovery()

        files = discover_files(source)
        if not files:
            handler.log_info(f"No JSON files found in {source}")
            return 0

        # builds index of (update_time, path, index) and sorts by update_time ascending
        index = build_conversation_index(files)
        index.sort(key=lambda x: x[0])

        handler.log_info(f"Found {len(index)} conversation(s) to process")
        handler.set_total(len(index))

        exporter = AppleNotesExporter(target="notes", cc_dir=cc_dir)

        # single upfront scan of destination folder
        note_index = exporter.scan_folder_notes(folder) if not dry_run else {}

        processed = 0
        failed = 0
        conversation_ids: list[str] = []

        for _update_time, file_path, conv_index in index:
            conv_id, success = _process_indexed_conversation(
                file_path,
                conv_index,
                exporter,
                folder,
                dry_run,
                overwrite,
                note_index,
                handler,
            )
            if conv_id:
                conversation_ids.append(conv_id)
            if success:
                processed += 1
            else:
                failed += 1

        # handles archive-deleted if requested
        if archive_deleted and not dry_run:
            _archive_deleted_notes(
                exporter, folder, conversation_ids, note_index, handler
            )

        handler.finish(processed, failed)

        if failed > 0:
            return 1
        return 0


def _process_indexed_conversation(
    file_path: Path,
    conv_index: int,
    exporter: AppleNotesExporter,
    folder: str,
    dry_run: bool,
    overwrite: bool,
    note_index: dict[str, NoteInfo],
    handler: ProgressHandler,
) -> tuple[Optional[str], bool]:
    """
    processes a single conversation by file path and index.

    Args:
        file_path: path to JSON file
        conv_index: index within list file, or -1 for dict file
        exporter: the AppleNotesExporter instance
        folder: destination folder name
        dry_run: if True, don't write to Apple Notes
        overwrite: if True, replace notes instead of appending
        note_index: map of conversation_id to NoteInfo
        handler: progress handler

    Returns:
        tuple of (conversation_id or None, success bool)
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            json_data = json.load(f)

        # extracts conversation data: dict file uses data directly, list file indexes
        conv_data = json_data if conv_index == -1 else json_data[conv_index]

        conversation = process_conversation(conv_data)
        handler.update(conversation.title)

        # looks up existing note from index
        existing = note_index.get(conversation.id)

        exporter.export(
            conversation=conversation,
            destination=folder,
            dry_run=dry_run,
            overwrite=overwrite,
            existing=existing,
            scanned=not dry_run,
        )

        return conversation.id, True

    except Exception as e:
        title = "Unknown"
        try:
            with open(file_path, encoding="utf-8") as f:
                json_data = json.load(f)
            if conv_index == -1:
                title = json_data.get("title", "Unknown")
            else:
                title = json_data[conv_index].get("title", "Unknown")
        except Exception:
            pass
        handler.log_error(f"Failed: {file_path.name} - {title}: {e}")
        handler.update(title)
        return None, False


def _archive_deleted_notes(
    exporter: AppleNotesExporter,
    folder: str,
    conversation_ids: list[str],
    note_index: dict[str, NoteInfo],
    handler: ProgressHandler,
) -> None:
    """moves notes not in conversation_ids to Archive subfolder."""
    source_ids = set(conversation_ids)

    archived = 0
    for conv_id, note_info in note_index.items():
        if conv_id not in source_ids and exporter.move_note_to_archive_by_id(
            note_info.note_id, folder
        ):
            handler.log_info(f"Archived: {conv_id}")
            archived += 1

    if archived:
        handler.log_info(f"Archived {archived} note(s)")
