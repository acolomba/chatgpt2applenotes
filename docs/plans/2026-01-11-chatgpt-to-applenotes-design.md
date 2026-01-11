# ChatGPT to Apple Notes - Design Document

**Date:** 2026-01-11
**Status:** Approved

## Overview

A Python tool to synchronize ChatGPT conversation exports (JSON format from chatgpt-exporter) to Apple Notes, with support for incremental updates and conversation archival.

## Project Goals

1. Port TypeScript conversation processing from chatgpt-exporter to Python
2. Generate byte-identical HTML output to validate the port
3. Implement Apple Notes HTML format exporter with sync capabilities
4. Provide CLI for batch processing files, directories, and ZIP archives

## Architecture

### Three-Layer Design

#### Layer 1: Core Processing

- `core/parser.py` - Direct port of `processConversation` from TypeScript
- `core/markdown_ast.py` - Markdown parsing to AST and custom HTML rendering
- `core/models.py` - Data structures mirroring TypeScript types

#### Layer 2: Exporters

- `exporters/base.py` - Abstract `Exporter` base class
- `exporters/html.py` - Reference HTML exporter (byte-identical to TypeScript output)
- `exporters/apple_notes.py` - Apple Notes format with sync metadata

#### Layer 3: Orchestration

- `sync.py` - File discovery, batch processing, error collection
- `cli.py` - Command-line interface

#### Data Flow

```text
JSON → parser.process_conversation() → normalized structure → exporter.export() → destination
```

## Project Structure

```text
chatgpt2applenotes/
├── chatgpt2applenotes/
│   ├── __init__.py
│   ├── cli.py                 # Command-line entry point
│   ├── sync.py                # Batch processing & orchestration
│   ├── core/
│   │   ├── __init__.py
│   │   ├── parser.py          # processConversation port
│   │   ├── markdown_ast.py    # Markdown parsing & rendering
│   │   └── models.py          # Data models
│   └── exporters/
│       ├── __init__.py
│       ├── base.py            # Abstract exporter
│       ├── html.py            # Reference HTML exporter
│       └── apple_notes.py     # Apple Notes exporter
├── tests/
│   ├── test_parser.py
│   ├── test_html_exporter.py
│   └── test_integration.py
├── output/                    # Generated files (git-ignored)
├── references/
│   └── apple-note-html.txt    # Apple Notes HTML format reference
├── validate.py                # Validation script
├── pyproject.toml
└── README.md
```

## TypeScript Port Strategy

### Direct Translation Approach

Port `processConversation` from `src/api.ts` maintaining:

- Same function logic and transformations
- Same variable names (converted to snake_case)
- Same conditional logic and edge cases
- Inline comments referencing TypeScript line numbers for traceability

### Key Translation Patterns

- TypeScript interfaces → Python `@dataclass` or `TypedDict`
- `Array.map/filter/reduce` → list comprehensions or explicit loops (match exact behavior)
- Date handling: TypeScript `Date` → Python `datetime` with identical ISO 8601 formatting
- String templates → f-strings preserving exact whitespace
- Optional/nullable types → `Optional[T]` with explicit None checks

### HTML Generation

Port HTML exporter from `src/exporter/html.ts` maintaining:

- Exact DOCTYPE, meta tags, CSS
- Same HTML structure for conversations and messages
- Identical class names and attributes
- Same escaping rules (using `html.escape()`)

### Markdown Rendering

Parse markdown with `markdown-it-py` (or `mistune`) to AST, then implement custom renderer controlling:

- Code block formatting (language tags, syntax highlighting)
- Link rendering (attributes, escaping)
- List formatting (spacing, nesting)
- Emphasis/strong tag choices

This ensures byte-identical output matching the TypeScript implementation.

## Validation Strategy

### Two-Phase Validation

#### Phase 1: Sample (5 files)

- Process test files:
  - ChatGPT-Freezing_Rye_Bread.json
  - ChatGPT-Fix_libflac_error.json
  - ChatGPT-Authentication_session_explained.json
  - ChatGPT-Best_Non-Alcoholic_Beer.json
  - ChatGPT-Wegovy_and_Glucose_Stabilization.json
- Write output to `output/html/`
- Byte-for-byte comparison using `filecmp.cmp()` against `/Users/acolomba/Downloads/chatgpt-export-html/`

#### Phase 2: Full Validation

- Process all JSON files in `/Users/acolomba/Downloads/chatgpt-export-json/`
- Compare against all reference HTML files
- Report: identical (✓), different (✗ with diff), missing

### Validation Tooling

Script or CLI subcommand `chatgpt2applenotes validate` that:

- Processes JSON files through HTML exporter
- Compares output to reference HTML
- Reports matches and discrepancies
- Exit code 0 only if all files match exactly

### Testing Approach

- Unit tests for `core/parser.py` functions using pytest
- Integration tests: sample JSON → compare to reference HTML
- Ralph Loop for iterative development: validate → fix → repeat until all match

### Error Handling

- Continue processing all files even if some fail
- Collect all errors and differences
- Final report: X/Y files matched, list of failures with reasons

## CLI Interface

### Commands

```bash
chatgpt2applenotes export <source> <destination> --format={html|applenotes} [options]
chatgpt2applenotes validate <source> <reference-dir>
```

### Arguments

- `<source>` - Path to JSON file, directory of JSON files, or ZIP file
- `<destination>` - Directory path (for html) or Apple Notes folder name (for applenotes)
- `--format` - Exporter type (default: html)

### Options

- `--dry-run` - Process files but don't write output (log what would happen)
- `--overwrite` - Behavior depends on format:
  - **HTML:** Overwrite existing files
  - **Apple Notes:** Replace entire note content (vs default append-only sync)
- `--prune-deleted` - Move conversations not in source to Archive subdirectory/subfolder
- `-v, --verbose` - Enable debug logging
- `--log-format={text|json}` - Structured logging format (default: text)

### File Handling

The `sync.py` module handles source discovery:

- **Single file:** Process one JSON file
- **Directory:** Glob `*.json` recursively
- **ZIP file:** Extract to temp, process files, cleanup after

Batch processing continues on errors, collecting results for final report.

## Apple Notes Integration

### Metadata Injection

The Apple Notes exporter injects metadata for sync:

**Conversation-level:**

```html
<div id="conv:<conversation_id> - <iso_timestamp>">
```

Placed after the note title, enables matching conversation exports to notes.

**Message-level:**

```html
<div id="msg:<message_id>">
```

Placed before each message block, enables identifying new messages during sync.

### Sync Logic

**Default behavior (no --overwrite):**

1. Search for existing note in destination folder by conversation ID from metadata
2. If found: Parse HTML, extract message IDs, determine new messages
3. Append only new messages to existing note
4. If not found: Create new note with full conversation

**With --overwrite flag:**

1. Find note by conversation ID
2. Replace entire content
3. Or create new note if doesn't exist

**With --prune-deleted flag:**

1. List all notes in destination folder
2. Extract conversation IDs from metadata
3. Compare to source conversation IDs
4. Move notes with IDs not in source to "Archive" subfolder

### Apple Notes HTML Format

Uses restricted HTML per `references/apple-note-html.txt`, ensuring compatibility with Apple Notes rendering engine.

Uses `macnotesapp` library for Apple Notes API interaction.

## Error Handling & Logging

### Error Categories

1. **Parse errors:** Malformed JSON, missing fields, unexpected structure
2. **Conversion errors:** Markdown rendering failures, invalid message types
3. **Export errors:** File write failures, Apple Notes API errors, permissions
4. **Sync errors:** Metadata parsing failures, duplicate IDs, corrupted notes

### Error Strategy

- Each layer catches and wraps exceptions with context (file, conversation ID, message ID)
- Errors bubble up to `sync.py` which collects and continues processing
- Final summary: total processed, successful, failed, skipped

### Logging Structure

Using Python's `logging` module with structured output:

**Standard (INFO level):**

```python
logger.info("Processing conversation", extra={
    "conversation_id": conv_id,
    "file": json_path,
    "message_count": len(messages)
})
```

**Verbose (DEBUG level):**

```python
logger.debug("Rendering markdown", extra={
    "message_id": msg_id,
    "markdown_length": len(content)
})
```

**Errors:**

```python
logger.error("Export failed", extra={
    "conversation_id": conv_id,
    "error": str(e),
    "traceback": traceback.format_exc()
})
```

**Log formats:**

- Text: Human-readable for terminal (`--log-format=text`)
- JSON: Machine-parseable for analysis (`--log-format=json`)

## Development Phases

### Phase 1: TypeScript Port & Validation

1. Port `processConversation` to `core/parser.py`
2. Port HTML exporter to `exporters/html.py`
3. Implement markdown AST rendering with custom HTML generator
4. Ralph Loop iteration: validate 5 files → fix differences → repeat
5. Expand to all files, iterate until 100% byte-identical match

**Success criteria:** All JSON files produce byte-identical HTML vs reference

### Phase 2: CLI & File Handling

1. Implement `sync.py` for file/directory/ZIP discovery
2. Build CLI with all flags and options
3. Add logging infrastructure (text and JSON formats)
4. Test with various input formats and error scenarios

**Success criteria:** CLI handles all input types with proper error reporting

### Phase 3: Apple Notes Integration

1. Study `macnotesapp` library capabilities
2. Implement Apple Notes HTML format generation
3. Build sync logic with metadata extraction and parsing
4. Test append-only updates, overwrite mode, and archival

**Success criteria:** Apple Notes sync appends new messages correctly, archival works

## Dependencies

```toml
dependencies = [
    "macnotesapp",           # Apple Notes integration
    "markdown-it-py",        # Markdown AST parsing
    # or "mistune" - TBD based on AST control needs
]
```

## Key Design Decisions

1. **Byte-for-byte matching:** Direct TypeScript port ensures exact HTML output for validation
2. **Layered architecture:** Clean separation between parsing, rendering, and export
3. **Markdown control:** Parse to AST, custom HTML renderer for exact output control
4. **Append-only sync:** Apple Notes updates append new messages, never modify existing (unless --overwrite)
5. **Continue on errors:** Process all files, report errors at end
6. **Structured logging:** JSON and text formats with configurable verbosity
7. **Archive on delete:** Optional `--prune-deleted` moves orphaned notes to Archive

## Success Criteria

- **Phase 1:** All JSON files produce byte-identical HTML compared to TypeScript reference
- **Phase 2:** CLI handles files/directories/ZIPs with proper error reporting and logging
- **Phase 3:** Apple Notes sync correctly appends new messages and archives deleted conversations

## Future Enhancements

- Invisible metadata in Apple Notes (explore if possible)
- Support for editing/updating existing messages (currently append-only)
- Bidirectional sync (Apple Notes → ChatGPT export format)
- Pythonic refactoring while maintaining test coverage
