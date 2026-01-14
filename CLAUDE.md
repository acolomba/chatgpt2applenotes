# CLAUDE.md

## Project Overview

Synchronizes ChatGPT conversation exports (JSON format from chatgpt-exporter) to Apple Notes, with support for incremental updates and conversation archival.

## Architecture

### Three-Layer Design

```text
chatgpt2applenotes/
├── __init__.py          # CLI entry point (main function)
├── sync.py              # batch processing & orchestration
├── core/
│   ├── models.py        # Conversation/Message dataclasses
│   └── parser.py        # JSON parsing, message extraction
└── exporters/
    ├── base.py          # abstract Exporter base class
    └── apple_notes.py   # Apple Notes exporter with sync
```

### Data Flow

```text
JSON → parser.process_conversation() → Conversation model → exporter.export() → Apple Notes
```

### Key Components

- **parser.py**: extracts messages from ChatGPT JSON export, handles message ordering and content normalization
- **models.py**: `Conversation` and `Message` dataclasses with metadata
- **apple_notes.py**: generates Apple Notes-compatible HTML, manages sync via AppleScript
  - renders markdown to HTML using markdown-it-py with custom renderers
  - tracks sync state via footer metadata (`{conversation_id}:{last_message_id}`)
  - supports incremental append (default) or full overwrite (`--overwrite`)
  - handles nested folders (`Parent/Child` syntax)

### Apple Notes Integration

Uses AppleScript directly (subprocess) for:

- creating/updating notes
- reading note content for sync comparison
- listing notes in folders
- moving notes to archive

### CLI Usage

```bash
chatgpt2applenotes <source> <folder> [--overwrite] [--archive-deleted]
```

- `<source>`: JSON file, directory of JSON files, or ZIP archive
- `<folder>`: Apple Notes folder name (supports `Parent/Child` nesting)
- `--overwrite`: replace entire note content instead of appending
- `--archive-deleted`: move notes not in source to Archive subfolder

## Guidelines

### Comments

Python docstrings and inline code comments in Python, YAML, shell, etc. are lowercase. The word "TODO" remains all-caps. Entities such as file names etc. preserve their casing.

Comments must be in the third-person, e.g. "installs", not "install", because they are descriptive. Avoid the imperative.

Keep comments concise, and non-obvious. Avoid documenting what everybody is expected to know.

### Python

Prefer Python idiomatic ("pythonic") style.

Always use type annotations.

### Code Formatting

Code formatting is handled automatically by pre-commit hooks (Black for Python, yamlfmt for YAML).

### Code Analysis

Respect the linters. NEVER change the linter configuration. If you're stuck in a loop, make a suggestion and pause for input.

### Git

- Git commit messages must be longer than 5 characters, and each line must be less than 80.
- You can expect pre-commit hooks to fail when attempting to commit. Fix the errors.
- NEVER use `--no-verify` to skip the hooks.
