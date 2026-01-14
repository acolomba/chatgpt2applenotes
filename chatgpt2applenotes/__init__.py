"""ChatGPT to Apple Notes converter."""

import argparse
import logging
from pathlib import Path
from typing import Optional

from chatgpt2applenotes.sync import sync_conversations

logger = logging.getLogger(__name__)


def main(argv: Optional[list[str]] = None) -> int:
    """
    main entry point for chatgpt2applenotes CLI.

    Args:
        argv: command line arguments (defaults to sys.argv[1:])

    Returns:
        exit code (0 success, 1 partial failure, 2 fatal error)
    """
    parser = argparse.ArgumentParser(
        description="Sync ChatGPT conversations to Apple Notes"
    )
    parser.add_argument(
        "source",
        help="JSON file, directory of JSON files, or ZIP archive",
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default="ChatGPT",
        help="Apple Notes folder name (default: ChatGPT)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="process files but don't write to Apple Notes",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace entire note content instead of appending",
    )
    parser.add_argument(
        "--archive-deleted",
        action="store_true",
        help="move notes not in source to Archive subfolder",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="enable debug logging",
    )

    args = parser.parse_args(argv)

    # configures logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(levelname)s] %(message)s",
    )

    # validates source path exists
    source_path = Path(args.source)
    if not source_path.exists():
        logger.error("Source not found: %s", args.source)
        return 2

    try:
        return sync_conversations(
            source=source_path,
            folder=args.folder,
            dry_run=args.dry_run,
            overwrite=args.overwrite,
            archive_deleted=args.archive_deleted,
        )
    except Exception as e:
        logger.error("Fatal error: %s", e)
        return 2
