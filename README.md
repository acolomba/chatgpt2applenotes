# ChatGPT to Apple Notes

[![CI](https://github.com/acolomba/chatgpt2applenotes/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/acolomba/chatgpt2applenotes/actions/workflows/ci.yml)

Synchronizes ChatGPT conversation exports to Apple Notes.

This project is a partial port of [chatgpt-exporter](https://github.com/pionxzh/chatgpt-exporter) and relies on the JSON export from that browser extension.

## Prerequisites

- macOS with Apple Notes
- Python 3.9+
- [chatgpt-exporter](https://github.com/pionxzh/chatgpt-exporter) browser extension to export conversations to JSON

## Installation

```sh
pip install chatgpt2applenotes
```

Or with [uv](https://docs.astral.sh/uv/):

```sh
uv tool install chatgpt2applenotes
```

## Usage

### Basic Usage

Sync all conversations from a ZIP export to an Apple Notes folder:

```sh
chatgpt2applenotes ~/Downloads/chatgpt-export.zip "ChatGPT"
```

Or:

```sh
chatgpt2applenotes ~/Downloads/chatgpt-export.zip
```

Nested folders are supported:

```sh
chatgpt2applenotes ~/Downloads/chatgpt-export.zip "Backups/Agents/ChatGPT"
```

### Input Sources

The source can be a ZIP archive, a directory of JSON files, or a single JSON file:

```sh
# ZIP archive (from chatgpt-exporter "Export All" option)
chatgpt2applenotes ~/Downloads/chatgpt-export.zip "ChatGPT"

# Directory of JSON files
chatgpt2applenotes ~/Downloads/chatgpt-exports/ "ChatGPT"

# Single conversation JSON file
chatgpt2applenotes ~/Downloads/conversation.json "ChatGPT"
```

### Options

#### `--overwrite`

By default, notes are updated incrementally: only new messages since the last sync are appended. Use `--overwrite` to rebuild notes from scratch.

```sh
chatgpt2applenotes ~/Downloads/chatgpt-export.zip --overwrite
```

#### `--archive-deleted`

Move notes for conversations no longer in the export to an "Archive" subfolder:

```sh
chatgpt2applenotes ~/Downloads/chatgpt-export.zip --archive-deleted
```

This is useful when you delete conversations in ChatGPT and want to keep the notes organized. Archived notes are moved to `<folder>/Archive`.

#### `--dry-run`

Process files without writing to Apple Notes. Useful for testing.

```sh
chatgpt2applenotes ~/Downloads/chatgpt-export.zip --dry-run
```

#### `--progress`

Show a progress bar during sync.

```sh
chatgpt2applenotes ~/Downloads/chatgpt-export.zip --progress
```

#### `-q/--quiet`

Suppress non-error output.

```sh
chatgpt2applenotes ~/Downloads/chatgpt-export.zip -q
```

#### `-v/--verbose`

Enable debug logging.

```sh
chatgpt2applenotes ~/Downloads/chatgpt-export.zip -v
```

#### `--cc DIR`

Save copies of generated HTML to a directory (useful for debugging). Works even with `--dry-run`.

```sh
chatgpt2applenotes ~/Downloads/chatgpt-export.zip --cc ~/debug-output/
```

### Exit Codes

- `0` - success
- `1` - partial failure (some conversations failed)
- `2` - fatal error

### Typical Workflow

1. Install the [chatgpt-exporter](https://github.com/pionxzh/chatgpt-exporter) browser extension.
2. In ChatGPT, choose the *Export* -> *Export All* -> *JSON (ZIP)* to export all conversations.
3. Open Apple Notes.
4. Run the sync on the downloaded Zip:

```sh
chatgpt2applenotes ~/Downloads/chatgpt-export-json.zip "ChatGPT"
```

### Periodic Sync

For regular backups, export your conversations periodically and run the sync. New conversations are added and the content of updated conversations is appended to the existing notes.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright 2025-2026 [Alessandro Colomba](https://github.com/acolomba)
