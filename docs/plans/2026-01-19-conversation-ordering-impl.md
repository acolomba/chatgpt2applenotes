# Conversation Ordering Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Process conversations in `update_time` ascending order so Apple Notes modification timestamps match ChatGPT's ordering.

**Architecture:** Two-pass processing - first pass stream-parses all files with ijson to build a lightweight index of `(update_time, path, index)` tuples, then sort by `update_time` ascending and process in that order.

**Tech Stack:** Python 3.9+, ijson for streaming JSON parsing

---

## Task 1: Add ijson Dependency

**Files:**

- Modify: `pyproject.toml:25-29`

Step 1. Add ijson to dependencies

In `pyproject.toml`, add `ijson` to the dependencies list:

```toml
dependencies = [
    "ijson~=3.2",
    "markdown-it-py~=3.0",
    "Pillow~=11.0",
    "rich~=13.9",
]
```

Step 2. Install dependency

Run: `pip install -e ".[dev]"`

Expected: Success, ijson installed

Step 3. Verify import works

Run: `python -c "import ijson; print(ijson.__version__)"`

Expected: Prints version (e.g., `3.2.3`)

Step 4. Commit

```bash
git add pyproject.toml
git commit -m "build: add ijson dependency for streaming JSON parsing"
```

---

## Task 2: Add mypy Override for ijson

**Files:**

- Modify: `pyproject.toml:97-99`

Step 1. Add ijson to mypy overrides

ijson doesn't have type stubs. Add it to the ignore list in `pyproject.toml`:

```toml
[[tool.mypy.overrides]]
module = ["requests", "hamcrest", "testcontainers.*", "tzlocal", "pytest", "markdown_it", "ijson"]
ignore_missing_imports = true
```

Step 2. Verify mypy passes

Run: `python -m mypy chatgpt2applenotes/`

Expected: Success (no errors)

Step 3. Commit

```bash
git add pyproject.toml
git commit -m "build: add mypy override for ijson"
```

---

## Task 3: Test Index Building for Single-Conversation Dict File

**Files:**

- Modify: `tests/test_sync.py`
- Create: `chatgpt2applenotes/sync.py` (add function)

Step 1. Write the failing test

Add to `tests/test_sync.py`:

```python
from chatgpt2applenotes.sync import build_conversation_index


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
```

Step 2. Run test to verify it fails

Run: `pytest tests/test_sync.py::test_build_index_single_conversation_dict -v`

Expected: FAIL with ImportError (function doesn't exist)

Step 3. Write minimal implementation

Add to `chatgpt2applenotes/sync.py`:

```python
import ijson


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
                    for i, update_time in enumerate(_extract_update_times_from_list(f)):
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
            return char[0]


def _extract_update_time_from_dict(f: Any) -> Optional[float]:
    """extracts update_time from a single conversation dict using streaming."""
    parser = ijson.parse(f)
    for prefix, event, value in parser:
        if prefix == "update_time" and event == "number":
            return float(value)
    return None


def _extract_update_times_from_list(f: Any) -> Iterator[float]:
    """yields update_time values from a list of conversations using streaming."""
    parser = ijson.parse(f)
    for prefix, event, value in parser:
        if prefix.endswith(".update_time") and event == "number":
            yield float(value)
```

Also add imports at top of file:

```python
from typing import Any, Iterator, Optional
```

Step 4. Run test to verify it passes

Run: `pytest tests/test_sync.py::test_build_index_single_conversation_dict -v`

Expected: PASS

Step 5. Commit

```bash
git add tests/test_sync.py chatgpt2applenotes/sync.py
git commit -m "feat: add build_conversation_index for single dict files"
```

---

## Task 4: Test Index Building for Multi-Conversation List File

**Files:**

- Modify: `tests/test_sync.py`

Step 1. Write the failing test

Add to `tests/test_sync.py`:

```python
def test_build_index_multi_conversation_list(tmp_path: Path) -> None:
    """builds index from multi-conversation list file."""
    conversations = [
        {"id": "conv-1", "title": "First", "create_time": 1000.0, "update_time": 3000.0, "mapping": {}},
        {"id": "conv-2", "title": "Second", "create_time": 1000.0, "update_time": 1000.0, "mapping": {}},
        {"id": "conv-3", "title": "Third", "create_time": 1000.0, "update_time": 2000.0, "mapping": {}},
    ]
    json_file = tmp_path / "multi.json"
    json_file.write_text(json.dumps(conversations), encoding="utf-8")

    index = build_conversation_index([json_file])

    assert len(index) == 3
    assert index[0] == (3000.0, json_file, 0)
    assert index[1] == (1000.0, json_file, 1)
    assert index[2] == (2000.0, json_file, 2)
```

Step 2. Run test to verify it passes

Run: `pytest tests/test_sync.py::test_build_index_multi_conversation_list -v`

Expected: PASS (implementation already handles this)

Step 3. Commit

```bash
git add tests/test_sync.py
git commit -m "test: add index building test for list files"
```

---

## Task 5: Test Index Building Skips Invalid Files

**Files:**

- Modify: `tests/test_sync.py`

Step 1. Write the failing test

Add to `tests/test_sync.py`:

```python
def test_build_index_skips_invalid_files(tmp_path: Path) -> None:
    """skips files that fail to parse."""
    valid = {"id": "conv-1", "title": "Valid", "create_time": 1000.0, "update_time": 2000.0, "mapping": {}}
    (tmp_path / "valid.json").write_text(json.dumps(valid), encoding="utf-8")
    (tmp_path / "invalid.json").write_text("not valid json", encoding="utf-8")

    index = build_conversation_index([tmp_path / "valid.json", tmp_path / "invalid.json"])

    assert len(index) == 1
    assert index[0][0] == 2000.0
```

Step 2. Run test to verify it passes

Run: `pytest tests/test_sync.py::test_build_index_skips_invalid_files -v`

Expected: PASS (implementation already handles this)

Step 3. Commit

```bash
git add tests/test_sync.py
git commit -m "test: add index building test for invalid files"
```

---

## Task 6: Test Index Building for Mixed Files

**Files:**

- Modify: `tests/test_sync.py`

Step 1. Write the failing test

Add to `tests/test_sync.py`:

```python
def test_build_index_mixed_files(tmp_path: Path) -> None:
    """builds index from mix of dict and list files."""
    dict_conv = {"id": "conv-1", "title": "Dict", "create_time": 1000.0, "update_time": 5000.0, "mapping": {}}
    list_conv = [
        {"id": "conv-2", "title": "List1", "create_time": 1000.0, "update_time": 3000.0, "mapping": {}},
        {"id": "conv-3", "title": "List2", "create_time": 1000.0, "update_time": 1000.0, "mapping": {}},
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
```

Step 2. Run test to verify it passes

Run: `pytest tests/test_sync.py::test_build_index_mixed_files -v`

Expected: PASS

Step 3. Commit

```bash
git add tests/test_sync.py
git commit -m "test: add index building test for mixed file types"
```

---

## Task 7: Test Sorted Processing Order

**Files:**

- Modify: `tests/test_sync.py`

Step 1. Write the failing test

Add to `tests/test_sync.py`:

```python
def test_sync_processes_in_update_time_order(tmp_path: Path) -> None:
    """sync processes conversations in update_time ascending order."""
    # creates files with different update_times
    old = {"id": "conv-old", "title": "Old", "create_time": 1000.0, "update_time": 1000.0, "mapping": {}}
    new = {"id": "conv-new", "title": "New", "create_time": 1000.0, "update_time": 3000.0, "mapping": {}}
    mid = {"id": "conv-mid", "title": "Mid", "create_time": 1000.0, "update_time": 2000.0, "mapping": {}}

    # names deliberately not in timestamp order
    (tmp_path / "z_new.json").write_text(json.dumps(new), encoding="utf-8")
    (tmp_path / "a_old.json").write_text(json.dumps(old), encoding="utf-8")
    (tmp_path / "m_mid.json").write_text(json.dumps(mid), encoding="utf-8")

    export_order: list[str] = []

    with patch("chatgpt2applenotes.sync.AppleNotesExporter") as mock_exporter_class:
        mock_exporter = MagicMock()
        mock_exporter_class.return_value = mock_exporter

        def track_export(conversation: Any, **kwargs: Any) -> None:
            export_order.append(conversation.id)

        mock_exporter.export.side_effect = track_export

        sync_conversations(tmp_path, "TestFolder", dry_run=True)

    # should be sorted by update_time ascending (oldest first)
    assert export_order == ["conv-old", "conv-mid", "conv-new"]
```

Step 2. Run test to verify it fails

Run: `pytest tests/test_sync.py::test_sync_processes_in_update_time_order -v`

Expected: FAIL (current code sorts by filename, not update_time)

Step 3. Modify sync_conversations to use index-based processing

Update `sync_conversations` in `chatgpt2applenotes/sync.py`:

Replace the current processing loop with:

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

        # builds index sorted by update_time ascending
        index = build_conversation_index(files)
        index.sort(key=lambda x: x[0])

        if not index:
            handler.log_info(f"No valid conversations found in {source}")
            return 0

        handler.log_info(f"Found {len(index)} conversation(s) to process")
        handler.set_total(len(index))

        exporter = AppleNotesExporter(target="notes", cc_dir=cc_dir)

        # single upfront scan of destination folder
        note_index = exporter.scan_folder_notes(folder) if not dry_run else {}

        processed = 0
        failed = 0
        conversation_ids: list[str] = []

        for update_time, file_path, conv_index in index:
            try:
                conv_id, success = _process_indexed_conversation(
                    file_path, conv_index, exporter, folder, dry_run, overwrite, note_index, handler
                )
                if conv_id:
                    conversation_ids.append(conv_id)
                if success:
                    processed += 1
                else:
                    failed += 1
            except Exception as e:
                handler.log_error(f"Failed to process {file_path.name}: {e}")
                handler.update(file_path.name)
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
        conv_index: index within file (-1 for dict, >= 0 for list)
        exporter: AppleNotesExporter instance
        folder: target folder name
        dry_run: if True, don't write to Apple Notes
        overwrite: if True, replace notes instead of appending
        note_index: pre-scanned note index
        handler: progress handler

    Returns:
        tuple of (conversation_id or None, success bool)
    """
    with open(file_path, encoding="utf-8") as f:
        json_data = json.load(f)

    # extracts the specific conversation
    if conv_index == -1:
        conv_data = json_data
    else:
        conv_data = json_data[conv_index]

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

        return conversation.id, True
    except Exception as e:
        title = conv_data.get("title", "Unknown")
        handler.log_error(f"Failed: {file_path.name} - {title}: {e}")
        handler.update(title)
        return None, False
```

Step 4. Run test to verify it passes

Run: `pytest tests/test_sync.py::test_sync_processes_in_update_time_order -v`

Expected: PASS

Step 5. Commit

```bash
git add tests/test_sync.py chatgpt2applenotes/sync.py
git commit -m "feat: process conversations in update_time ascending order"
```

---

## Task 8: Remove Old _process_file Function

**Files:**

- Modify: `chatgpt2applenotes/sync.py`

Step 1. Remove unused function

Delete the `_process_file` function from `sync.py` (it's no longer used after Task 7).

Step 2. Run all tests to verify nothing broke

Run: `pytest tests/test_sync.py -v`

Expected: All tests PASS

Step 3. Run full test suite

Run: `pytest -q`

Expected: All tests PASS

Step 4. Commit

```bash
git add chatgpt2applenotes/sync.py
git commit -m "refactor: remove unused _process_file function"
```

---

## Task 9: Run Type Checking and Linters

**Files:**

- Potentially modify: `chatgpt2applenotes/sync.py`

Step 1. Run mypy

Run: `python -m mypy chatgpt2applenotes/`

Expected: Success (no errors)

Step 2. Run ruff

Run: `python -m ruff check chatgpt2applenotes/`

Expected: Success (no errors)

Step 3. Run pylint

Run: `python -m pylint chatgpt2applenotes/`

Expected: Success (score 10/10 or acceptable)

Step 4. Fix any issues found

If issues found, fix them and run checks again.

Step 5. Commit if changes made

```bash
git add chatgpt2applenotes/
git commit -m "fix: address linter issues"
```

---

## Task 10: Final Integration Test

**Files:**

- None (verification only)

Step 1. Run full test suite

Run: `pytest -v`

Expected: All 124+ tests PASS

Step 2. Run pre-commit on all files

Run: `pre-commit run --all-files`

Expected: All checks PASS

Step 3. Verify git status is clean

Run: `git status`

Expected: Working tree clean (all changes committed)

---

## Summary

After completing all tasks:

1. `ijson` is added as a dependency
2. `build_conversation_index()` stream-parses files to build lightweight index
3. `sync_conversations()` processes in `update_time` ascending order
4. Progress bar shows accurate conversation count upfront
5. All tests pass, linters clean
