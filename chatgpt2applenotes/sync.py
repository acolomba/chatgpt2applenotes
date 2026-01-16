"""Sync module for batch processing conversations."""

import json
import logging
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

from chatgpt2applenotes.core.parser import process_conversation
from chatgpt2applenotes.exporters.apple_notes import AppleNotesExporter
from chatgpt2applenotes.exporters.applescript import NoteInfo

logger = logging.getLogger(__name__)


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

    Returns:
        exit code (0 success, 1 partial failure, 2 fatal error)
    """
    files = discover_files(source)
    if not files:
        logger.warning("No JSON files found in %s", source)
        return 0

    logger.info("Found %d conversation(s) to process", len(files))

    exporter = AppleNotesExporter(target="notes", cc_dir=cc_dir)

    # single upfront scan of destination folder
    note_index = exporter.scan_folder_notes(folder) if not dry_run else {}

    processed = 0
    failed = 0
    conversation_ids: list[str] = []

    for json_path in files:
        try:
            result = _process_file(
                json_path, exporter, folder, dry_run, overwrite, note_index
            )
            if result:
                conversation_ids.append(result)
                processed += 1
        except Exception as e:
            logger.error("Failed: %s - %s", json_path.name, e)
            failed += 1

    # handles archive-deleted if requested
    if archive_deleted and not dry_run:
        _archive_deleted_notes(exporter, folder, conversation_ids, note_index)

    # prints summary
    logger.info(
        "Processed %d conversation(s): %d synced, %d failed",
        processed + failed,
        processed,
        failed,
    )

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
) -> Optional[str]:
    """
    processes a single JSON file.

    Returns:
        conversation ID if successful, None otherwise
    """
    with open(json_path, encoding="utf-8") as f:
        json_data = json.load(f)

    conversation = process_conversation(json_data)
    logger.debug("Processing: %s", conversation.title)

    # looks up existing note from index
    existing = note_index.get(conversation.id)

    exporter.export(
        conversation=conversation,
        destination=folder,
        dry_run=dry_run,
        overwrite=overwrite,
        existing=existing,
        scanned=not dry_run,  # we scanned the folder unless in dry_run mode
    )

    return conversation.id


def _archive_deleted_notes(
    exporter: AppleNotesExporter,
    folder: str,
    conversation_ids: list[str],
    note_index: dict[str, NoteInfo],
) -> None:
    """moves notes not in conversation_ids to Archive subfolder."""
    source_ids = set(conversation_ids)

    archived = 0
    for conv_id, note_info in note_index.items():
        if conv_id not in source_ids and exporter.move_note_to_archive_by_id(
            note_info.note_id, folder
        ):
            logger.info("Archived: %s", conv_id)
            archived += 1

    if archived:
        logger.info("Archived %d note(s)", archived)
