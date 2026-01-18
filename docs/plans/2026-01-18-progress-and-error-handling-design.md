# Progress Bar and Error Handling Design

## Overview

Adds support for multi-conversation files with per-conversation error handling, accurate conversation counting, and a `--progress` option with an updating progress bar.

## CLI Options

**New options:**

- `--progress` - show an updating progress bar
- `--quiet` - suppress all non-error output

**Behavior matrix:**

| Flags                | INFO logs | Errors | Summary | Progress bar |
| -------------------- | --------- | ------ | ------- | ------------ |
| (default)            | ✓         | ✓      | ✓       | ✗            |
| `--quiet`            | ✗         | ✓      | ✗       | ✗            |
| `--progress`         | ✗         | ✓      | ✓       | ✓            |
| `--progress --quiet` | ✗         | ✓      | ✗       | ✓            |

**Progress bar format:**

```text
[████████░░░░] 8/12 - "How to make pasta"
```

During initial file discovery:

```text
⠋ Discovering conversations...
```

## Architecture

### New Module: `chatgpt2applenotes/progress.py`

Encapsulates all progress/output handling:

```python
class ProgressHandler:
    def __init__(self, quiet: bool, show_progress: bool):
        self.quiet = quiet
        self.show_progress = show_progress
        self.console = Console(stderr=True)
        self._progress: Optional[Progress] = None
        self._task_id: Optional[TaskID] = None

    def start_discovery(self) -> None:
        # starts spinner: "Discovering conversations..."

    def set_total(self, total: int) -> None:
        # switches from spinner to progress bar

    def adjust_total(self, delta: int) -> None:
        # increases total when multi-conversation file found

    def update(self, title: str) -> None:
        # advances by 1, updates description to show title

    def log_error(self, message: str) -> None:
        # prints error (respects progress bar if active)

    def finish(self, processed: int, failed: int) -> None:
        # stops progress, prints summary unless quiet
```

Used as a context manager for cleanup:

```python
with ProgressHandler(quiet, progress) as handler:
    handler.start_discovery()
    ...
```

### Changes to Existing Modules

**`chatgpt2applenotes/__init__.py`:**

- Add `--progress` and `--quiet` CLI arguments
- Pass them to `sync_conversations()`

**`chatgpt2applenotes/sync.py`:**

- Accept `quiet` and `progress` parameters in `sync_conversations()`
- Create and use `ProgressHandler` instance
- Replace direct `logger.info()` calls with handler methods
- Route `logger.error()` through `handler.log_error()`

**`pyproject.toml`:**

- Add `rich` dependency

## Dynamic Progress Counting

Initial total equals number of files discovered. When a file contains multiple conversations, dynamically adjust the total.

**Example flow:**

```text
Files discovered: 10
Initial total: 10

File 1: 1 conversation  → total stays 10, progress 1/10
File 2: 3 conversations → total becomes 12, progress 2/12, 3/12, 4/12
File 3: 1 conversation  → progress 5/12
...
```

**Implementation:**

```python
handler.set_total(len(files))  # initial estimate

for json_path in files:
    conversations = load_and_normalize(json_path)
    if len(conversations) > 1:
        handler.adjust_total(len(conversations) - 1)

    for conv_data in conversations:
        # process one at a time
```

This maintains the current memory profile (one file loaded at a time) while providing accurate progress.

## Partial Failure Handling

Each conversation is processed independently. When one fails:

1. Error is logged with source filename for context
2. Processing continues with remaining conversations
3. Failed conversation is not added to `conversation_ids` (affects archive-deleted logic)
4. Exit code 1 indicates partial failure

## Edge Cases

| Scenario                        | Behavior                                               |
| ------------------------------- | ------------------------------------------------------ |
| No files found                  | No progress bar shown, just warning log                |
| All conversations fail          | Progress completes, summary shows "0 synced, N failed" |
| Empty JSON array `[]`           | File contributes 0 to progress, no error               |
| `--progress` with single file   | Still shows progress bar                               |
| Terminal doesn't support colors | Rich auto-detects and falls back                       |

## Files to Modify

1. `pyproject.toml` - add `rich` dependency
2. `chatgpt2applenotes/__init__.py` - add CLI arguments
3. `chatgpt2applenotes/progress.py` - new file
4. `chatgpt2applenotes/sync.py` - integrate handler, refactor error handling
5. `tests/test_progress.py` - new tests

## Testing

- **Unit tests for `ProgressHandler`**: mock `rich.Console`, verify correct methods called
- **Integration tests**: capture stderr, verify output format
- **Manual testing**: visual verification with real terminal
