"""Sync module for batch processing conversations."""

import json
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

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

        handler.log_info(f"Found {len(files)} file(s) to process")
        handler.set_total(len(files))

        exporter = AppleNotesExporter(target="notes", cc_dir=cc_dir)

        # single upfront scan of destination folder
        note_index = exporter.scan_folder_notes(folder) if not dry_run else {}

        processed = 0
        failed = 0
        conversation_ids: list[str] = []

        for json_path in files:
            try:
                ids, conv_failed = _process_file(
                    json_path, exporter, folder, dry_run, overwrite, note_index, handler
                )
                conversation_ids.extend(ids)
                processed += len(ids)
                failed += conv_failed
            except Exception as e:
                handler.log_error(f"Failed to load {json_path.name}: {e}")
                handler.update(json_path.name)
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


def _process_file(
    json_path: Path,
    exporter: AppleNotesExporter,
    folder: str,
    dry_run: bool,
    overwrite: bool,
    note_index: dict[str, NoteInfo],
    handler: ProgressHandler,
) -> tuple[list[str], int]:
    """
    processes a single JSON file containing one or more conversations.

    Returns:
        tuple of (list of conversation IDs successfully processed, count of failures)
    """
    with open(json_path, encoding="utf-8") as f:
        json_data = json.load(f)

    # normalizes to list (ChatGPT exports single conversations as a list too)
    conversations_data = json_data if isinstance(json_data, list) else [json_data]

    # adjusts total if file has multiple conversations
    if len(conversations_data) > 1:
        handler.adjust_total(len(conversations_data) - 1)

    conversation_ids = []
    failed = 0

    for conv_data in conversations_data:
        try:
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

            conversation_ids.append(conversation.id)
        except Exception as e:
            title = conv_data.get("title", "Unknown")
            handler.log_error(f"Failed: {json_path.name} - {title}: {e}")
            handler.update(title)
            failed += 1

    return conversation_ids, failed


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
