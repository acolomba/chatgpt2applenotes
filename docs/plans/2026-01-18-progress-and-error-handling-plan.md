# Progress Bar and Error Handling Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `--progress` and `--quiet` CLI options with per-conversation error handling and accurate conversation counting.

**Architecture:** New `ProgressHandler` class in `progress.py` encapsulates all output logic. The sync loop delegates logging/progress to this handler, enabling clean separation between orchestration and presentation.

**Tech Stack:** Python 3.9+, rich library for progress bars, pytest for testing.

---

## Task 1: Add rich Dependency

**Files:

- Modify: `pyproject.toml:25-28`

### Step 1: Add rich to dependencies

Edit `pyproject.toml` to add rich to the dependencies list:

```toml
dependencies = [
    "markdown-it-py~=3.0",
    "Pillow~=11.0",
    "rich~=13.9",
]
```

### Step 2: Install dependencies

Run: `uv sync`

Expected: Dependencies installed successfully, including rich.

### Step 3: Verify installation

Run: `uv run python -c "from rich.progress import Progress; print('ok')"`

Expected: `ok`

### Step 4: Commit

```bash
git add pyproject.toml uv.lock
git commit -m "build: add rich dependency for progress bar support"
```

---

## Task 2: Create ProgressHandler with Basic Structure

**Files:

- Create: `chatgpt2applenotes/progress.py`
- Create: `tests/test_progress.py`

### Step 1: Write the failing test for ProgressHandler initialization

Create `tests/test_progress.py`:

```python
"""tests for progress module."""

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
```

### Step 2: Run test to verify it fails

Run: `uv run pytest tests/test_progress.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'chatgpt2applenotes.progress'`

### Step 3: Write minimal implementation

Create `chatgpt2applenotes/progress.py`:

```python
"""progress and output handling for sync operations."""

from typing import Optional

from rich.console import Console
from rich.progress import Progress, TaskID


class ProgressHandler:
    """handles progress display and output for sync operations."""

    def __init__(self, quiet: bool = False, show_progress: bool = False) -> None:
        self.quiet = quiet
        self.show_progress = show_progress
        self._console = Console(stderr=True)
        self._progress: Optional[Progress] = None
        self._task_id: Optional[TaskID] = None
```

### Step 4: Run test to verify it passes

Run: `uv run pytest tests/test_progress.py -v`

Expected: PASS

### Step 5: Commit

```bash
git add chatgpt2applenotes/progress.py tests/test_progress.py
git commit -m "feat: add ProgressHandler class skeleton"
```

---

## Task 3: Add Context Manager Support

**Files:

- Modify: `chatgpt2applenotes/progress.py`
- Modify: `tests/test_progress.py`

### Step 1: Write the failing test for context manager

Add to `tests/test_progress.py`:

```python
def test_progress_handler_context_manager() -> None:
    """ProgressHandler works as context manager."""
    with ProgressHandler() as handler:
        assert handler is not None
```

### Step 2: Run test to verify it fails

Run: `uv run pytest tests/test_progress.py::test_progress_handler_context_manager -v`

Expected: FAIL with `AttributeError: __enter__`

### Step 3: Write minimal implementation

Add to `ProgressHandler` class in `progress.py`:

```python
    def __enter__(self) -> "ProgressHandler":
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[object],
    ) -> None:
        if self._progress is not None:
            self._progress.stop()
            self._progress = None
```

### Step 4: Run test to verify it passes

Run: `uv run pytest tests/test_progress.py::test_progress_handler_context_manager -v`

Expected: PASS

### Step 5: Commit

```bash
git add chatgpt2applenotes/progress.py tests/test_progress.py
git commit -m "feat: add context manager support to ProgressHandler"
```

---

## Task 4: Add start_discovery Method (Spinner)

**Files:

- Modify: `chatgpt2applenotes/progress.py`
- Modify: `tests/test_progress.py`

### Step 1: Write the failing test

Add to `tests/test_progress.py`:

```python
from unittest.mock import MagicMock, patch


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
```

### Step 2: Run test to verify it fails

Run: `uv run pytest tests/test_progress.py::test_start_discovery_shows_spinner_when_progress_enabled -v`

Expected: FAIL with `AttributeError: 'ProgressHandler' object has no attribute 'start_discovery'`

### Step 3: Write minimal implementation

Add to `ProgressHandler` class in `progress.py`:

```python
    def start_discovery(self) -> None:
        """starts spinner for discovery phase."""
        if not self.show_progress:
            return

        self._progress = Progress(
            "[progress.description]{task.description}",
            console=self._console,
            transient=True,
        )
        self._progress.start()
        self._task_id = self._progress.add_task(
            "Discovering conversations...", total=None
        )
```

Also add this import at the top of the file:

```python
from rich.progress import Progress, SpinnerColumn, TaskID
```

### Step 4: Run tests to verify they pass

Run: `uv run pytest tests/test_progress.py -v -k "start_discovery"`

Expected: PASS

### Step 5: Commit

```bash
git add chatgpt2applenotes/progress.py tests/test_progress.py
git commit -m "feat: add start_discovery spinner to ProgressHandler"
```

---

## Task 5: Add set_total Method (Switch to Determinate Bar)

**Files:

- Modify: `chatgpt2applenotes/progress.py`
- Modify: `tests/test_progress.py`

### Step 1: Write the failing test

Add to `tests/test_progress.py`:

```python
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
```

### Step 2: Run test to verify it fails

Run: `uv run pytest tests/test_progress.py::test_set_total_switches_to_determinate_progress -v`

Expected: FAIL with `AttributeError: 'ProgressHandler' object has no attribute 'set_total'`

### Step 3: Write minimal implementation

Add imports at top of `progress.py`:

```python
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
)
```

Add to `ProgressHandler` class:

```python
    def set_total(self, total: int) -> None:
        """switches from spinner to determinate progress bar."""
        if not self.show_progress:
            return

        # stops spinner
        if self._progress is not None:
            self._progress.stop()

        # starts determinate progress bar
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("- {task.fields[title]}"),
            console=self._console,
            transient=True,
        )
        self._progress.start()
        self._task_id = self._progress.add_task(
            "Syncing", total=total, title=""
        )
        self._total = total
```

Also add `self._total = 0` to `__init__`.

### Step 4: Run tests to verify they pass

Run: `uv run pytest tests/test_progress.py -v -k "set_total"`

Expected: PASS

### Step 5: Commit

```bash
git add chatgpt2applenotes/progress.py tests/test_progress.py
git commit -m "feat: add set_total to switch to determinate progress bar"
```

---

## Task 6: Add adjust_total and update Methods

**Files:

- Modify: `chatgpt2applenotes/progress.py`
- Modify: `tests/test_progress.py`

### Step 1: Write the failing tests

Add to `tests/test_progress.py`:

```python
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
```

### Step 2: Run tests to verify they fail

Run: `uv run pytest tests/test_progress.py -v -k "adjust_total or update_advances"`

Expected: FAIL with `AttributeError`

### Step 3: Write minimal implementation

Add to `ProgressHandler` class:

```python
    def adjust_total(self, delta: int) -> None:
        """increases total when multi-conversation file found."""
        if not self.show_progress or self._progress is None or self._task_id is None:
            return

        self._total += delta
        self._progress.update(self._task_id, total=self._total)

    def update(self, title: str) -> None:
        """advances progress by 1 and updates current title."""
        if not self.show_progress or self._progress is None or self._task_id is None:
            return

        self._progress.update(self._task_id, advance=1, title=title)
```

### Step 4: Run tests to verify they pass

Run: `uv run pytest tests/test_progress.py -v -k "adjust_total or update_advances"`

Expected: PASS

### Step 5: Commit

```bash
git add chatgpt2applenotes/progress.py tests/test_progress.py
git commit -m "feat: add adjust_total and update methods to ProgressHandler"
```

---

## Task 7: Add log_error and finish Methods

**Files:

- Modify: `chatgpt2applenotes/progress.py`
- Modify: `tests/test_progress.py`

### Step 1: Write the failing tests

Add to `tests/test_progress.py`:

```python
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
```

### Step 2: Run tests to verify they fail

Run: `uv run pytest tests/test_progress.py -v -k "log_error or finish"`

Expected: FAIL with `AttributeError`

### Step 3: Write minimal implementation

Add to `ProgressHandler` class:

```python
    def log_error(self, message: str) -> None:
        """prints error message (always shown, even in quiet mode)."""
        self._console.print(f"[red]ERROR:[/red] {message}")

    def finish(self, processed: int, failed: int) -> None:
        """stops progress and prints summary unless quiet."""
        if self._progress is not None:
            self._progress.stop()
            self._progress = None

        if self.quiet:
            return

        total = processed + failed
        self._console.print(
            f"Processed {total} conversation(s): {processed} synced, {failed} failed"
        )
```

### Step 4: Run tests to verify they pass

Run: `uv run pytest tests/test_progress.py -v -k "log_error or finish"`

Expected: PASS

### Step 5: Commit

```bash
git add chatgpt2applenotes/progress.py tests/test_progress.py
git commit -m "feat: add log_error and finish methods to ProgressHandler"
```

---

## Task 8: Add log_info Method

**Files:

- Modify: `chatgpt2applenotes/progress.py`
- Modify: `tests/test_progress.py`

### Step 1: Write the failing tests

Add to `tests/test_progress.py`:

```python
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
```

### Step 2: Run tests to verify they fail

Run: `uv run pytest tests/test_progress.py -v -k "log_info"`

Expected: FAIL with `AttributeError`

### Step 3: Write minimal implementation

Add to `ProgressHandler` class:

```python
    def log_info(self, message: str) -> None:
        """prints info message (only when not quiet and progress disabled)."""
        if self.quiet or self.show_progress:
            return

        self._console.print(message)
```

### Step 4: Run tests to verify they pass

Run: `uv run pytest tests/test_progress.py -v -k "log_info"`

Expected: PASS

### Step 5: Commit

```bash
git add chatgpt2applenotes/progress.py tests/test_progress.py
git commit -m "feat: add log_info method to ProgressHandler"
```

---

## Task 9: Add --progress and --quiet CLI Arguments

**Files:

- Modify: `chatgpt2applenotes/__init__.py`
- Modify: `tests/test_cli.py`

### Step 1: Write the failing tests

Add to `tests/test_cli.py`:

```python
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
```

### Step 2: Run tests to verify they fail

Run: `uv run pytest tests/test_cli.py -v -k "progress or quiet"`

Expected: FAIL with `error: unrecognized arguments: --progress`

### Step 3: Write minimal implementation

Add to `chatgpt2applenotes/__init__.py` after the `--cc` argument:

```python
    parser.add_argument(
        "--progress",
        action="store_true",
        help="show progress bar during sync",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="suppress all non-error output",
    )
```

And update the `sync_conversations` call to pass the new arguments:

```python
        return sync_conversations(
            source=source_path,
            folder=args.folder,
            dry_run=args.dry_run,
            overwrite=args.overwrite,
            archive_deleted=args.archive_deleted,
            cc_dir=cc_dir,
            quiet=args.quiet,
            progress=args.progress,
        )
```

### Step 4: Run tests to verify they pass

Run: `uv run pytest tests/test_cli.py -v -k "progress or quiet"`

Expected: FAIL (sync_conversations doesn't accept quiet/progress yet - that's expected)

### Step 5: Commit CLI changes only

```bash
git add chatgpt2applenotes/__init__.py tests/test_cli.py
git commit -m "feat: add --progress and --quiet CLI arguments"
```

---

## Task 10: Integrate ProgressHandler into sync_conversations

**Files:

- Modify: `chatgpt2applenotes/sync.py`
- Modify: `tests/test_sync.py`

### Step 1: Write the failing test

Add to `tests/test_sync.py`:

```python
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
```

### Step 2: Run test to verify it fails

Run: `uv run pytest tests/test_sync.py::test_sync_accepts_quiet_and_progress_args -v`

Expected: FAIL with `TypeError: sync_conversations() got an unexpected keyword argument 'quiet'`

### Step 3: Write the implementation

Update `sync_conversations` in `chatgpt2applenotes/sync.py`:

```python
from chatgpt2applenotes.progress import ProgressHandler
```

Update function signature:

```python
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
```

Replace the function body with:

```python
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
            _archive_deleted_notes(exporter, folder, conversation_ids, note_index)

        handler.finish(processed, failed)

        if failed > 0:
            return 1
        return 0
```

### Step 4: Update _process_file to handle per-conversation errors

Update `_process_file` signature and body:

```python
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
```

### Step 4: Run tests to verify they pass

Run: `uv run pytest tests/test_sync.py -v`

Expected: Some tests may fail due to changed function signature - we'll fix those in the next task.

### Step 5: Commit

```bash
git add chatgpt2applenotes/sync.py tests/test_sync.py
git commit -m "feat: integrate ProgressHandler into sync_conversations"
```

---

## Task 11: Fix Existing Tests

**Files:

- Modify: `tests/test_sync.py`

### Step 1: Run all sync tests to identify failures

Run: `uv run pytest tests/test_sync.py -v`

Identify which tests fail due to the changed `_process_file` signature.

### Step 2: Update test mocks

Tests that mock `_process_file` or check `exporter.export` call counts may need updates. The key changes:

1. `_process_file` now returns `tuple[list[str], int]` instead of `list[str]`
2. `_process_file` now takes a `handler` parameter

Update any affected tests to use `patch("chatgpt2applenotes.sync.ProgressHandler")` to provide a mock handler.

### Step 3: Run all tests

Run: `uv run pytest tests/ -v`

Expected: PASS

### Step 4: Commit

```bash
git add tests/test_sync.py
git commit -m "test: update sync tests for ProgressHandler integration"
```

---

## Task 12: Add Multi-Conversation File Test

**Files:

- Modify: `tests/test_sync.py`

### Step 1: Write the test for multi-conversation file handling

Add to `tests/test_sync.py`:

```python
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
    # creates a file with one valid and one invalid conversation
    conversations = [
        {
            "id": "conv-1",
            "title": "Valid",
            "create_time": 1234567890.0,
            "update_time": 1234567890.0,
            "mapping": {},
        },
        {
            # missing required fields - will fail parsing
            "title": "Invalid",
        },
    ]
    (tmp_path / "mixed.json").write_text(json.dumps(conversations), encoding="utf-8")

    with patch("chatgpt2applenotes.sync.AppleNotesExporter") as mock_exporter_class:
        mock_exporter = MagicMock()
        mock_exporter_class.return_value = mock_exporter

        result = sync_conversations(tmp_path, "TestFolder", dry_run=True)

    # returns 1 (partial failure)
    assert result == 1
    # but still processed the valid conversation
    assert mock_exporter.export.call_count == 1
```

### Step 2: Run tests

Run: `uv run pytest tests/test_sync.py -v -k "multi_conversation or conversation_failure"`

Expected: PASS (if implementation is correct)

### Step 3: Commit

```bash
git add tests/test_sync.py
git commit -m "test: add multi-conversation file handling tests"
```

---

## Task 13: Run Full Test Suite and Linters

**Files:** None (validation only)

### Step 1: Run full test suite

Run: `uv run pytest tests/ -v`

Expected: All tests pass.

### Step 2: Run type checker

Run: `uv run mypy chatgpt2applenotes/`

Expected: No errors (may need to add type stubs for rich to mypy config).

### Step 3: Run linters

Run: `uv run ruff check chatgpt2applenotes/ tests/`

Expected: No errors.

### Step 4: If mypy complains about rich, add override to pyproject.toml

```toml
[[tool.mypy.overrides]]
module = "rich.*"
ignore_missing_imports = true
```

### Step 5: Commit any fixes

```bash
git add -A
git commit -m "fix: address linter and type checker issues"
```

---

## Task 14: Manual Testing

**Files:** None (manual verification)

### Step 1: Test with --progress flag

Run: `uv run chatgpt2applenotes <test-file.json> TestFolder --progress --dry-run`

Expected: See progress bar with spinner, then determinate progress.

### Step 2: Test with --quiet flag

Run: `uv run chatgpt2applenotes <test-file.json> TestFolder --quiet --dry-run`

Expected: No output except errors.

### Step 3: Test with both flags

Run: `uv run chatgpt2applenotes <test-file.json> TestFolder --progress --quiet --dry-run`

Expected: Progress bar shown, no summary printed.

### Step 4: Test with multi-conversation file

Create a test file with multiple conversations and verify progress bar adjusts correctly.

---

## Summary

After completing all tasks, you will have:

1. `rich` dependency added for progress bar support
2. New `chatgpt2applenotes/progress.py` with `ProgressHandler` class
3. `--progress` and `--quiet` CLI options
4. Per-conversation error handling (continues after failures)
5. Accurate conversation counting in progress bar
6. Dynamic total adjustment for multi-conversation files
7. Comprehensive test coverage
