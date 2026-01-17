# Sync Performance Optimization

## Problem

Synchronization slows down significantly as conversations accumulate. For 200+ conversations, the process becomes painfully slow.

**Root cause:** For every conversation being synced, the code scans all notes in the destination folder to find a matching note by conversation ID embedded in the body. This results in O(N×M) AppleScript iterations where N = conversations to sync and M = existing notes.

**Current flow:**

```text
for each conversation:
    for each note in folder:        # AppleScript loop
        if note body contains conversation_id:
            return note body
```

## Solution

Scan the destination folder once upfront, build an index of existing notes, then use direct note ID lookups for all operations.

**New flow:**

```text
note_index = scan_folder_once()     # O(M) calls, each O(1)
for each conversation:
    existing = note_index.get(conversation_id)  # O(1) lookup
    if existing:
        update_note_by_id(existing.note_id, ...)  # O(1) call
    else:
        create_new_note(...)
```

## Data Model

New dataclass in `chatgpt2applenotes/exporters/applescript.py`:

```python
@dataclass
class NoteInfo:
    """metadata for an existing Apple Note."""
    note_id: str              # Apple Notes internal ID (x-coredata://...)
    conversation_id: str      # extracted from footer
    last_message_id: str      # extracted from footer
```

Index type: `dict[str, NoteInfo]` keyed by conversation_id.

## AppleScript Changes

### New Functions

**`list_note_ids(folder: str) -> list[str]`**

Returns all note IDs in folder with a single AppleScript call:

```applescript
tell application "Notes"
    set notesList to every note of {folder_ref}
    set result to ""
    repeat with aNote in notesList
        set result to result & (id of aNote) & linefeed
    end repeat
    return result
end tell
```

**`read_note_body_by_id(note_id: str) -> Optional[str]`**

Reads note body by direct ID lookup:

```applescript
tell application "Notes"
    set theNote to note id "{note_id}"
    return body of theNote
end tell
```

**`scan_folder_notes(folder: str) -> dict[str, NoteInfo]`**

Python function that orchestrates the two-phase scan:

```python
def scan_folder_notes(folder: str) -> dict[str, NoteInfo]:
    """scans folder and builds conversation_id -> NoteInfo index."""
    note_ids = list_note_ids(folder)
    index = {}
    for note_id in note_ids:
        body = read_note_body_by_id(note_id)
        if body:
            conv_id, msg_id = parse_footer(body)
            if conv_id:
                index[conv_id] = NoteInfo(note_id, conv_id, msg_id)
    return index
```

**`update_note_by_id(note_id: str, html_content: str) -> bool`**

Replaces note body by direct ID:

```applescript
tell application "Notes"
    set theNote to note id "{note_id}"
    set body of theNote to htmlContent
end tell
```

**`append_to_note_by_id(note_id: str, html_content: str) -> bool`**

Appends to note by direct ID:

```applescript
tell application "Notes"
    set theNote to note id "{note_id}"
    set body of theNote to (body of theNote) & htmlContent
end tell
```

**`delete_note_by_id(note_id: str) -> bool`**

Deletes note by direct ID:

```applescript
tell application "Notes"
    delete note id "{note_id}"
end tell
```

**`move_note_to_archive_by_id(note_id: str, folder: str) -> bool`**

Moves note to Archive subfolder by direct ID:

```applescript
tell application "Notes"
    set theNote to note id "{note_id}"
    -- create Archive subfolder if needed
    if not (exists folder "Archive" of {folder_ref}) then
        make new folder at {folder_ref} with properties {name:"Archive"}
    end if
    move theNote to folder "Archive" of {folder_ref}
end tell
```

## Sync Orchestration Changes

### sync.py

```python
def sync_conversations(source, folder, dry_run, overwrite, archive_deleted, cc_dir):
    files = discover_files(source)
    if not files:
        return 0

    exporter = AppleNotesExporter(target="notes", cc_dir=cc_dir)

    # single upfront scan - O(M) where M = existing notes
    note_index = exporter.scan_folder_notes(folder)

    source_conv_ids = set()
    processed = 0
    failed = 0

    for json_path in files:
        try:
            conversation = load_conversation(json_path)
            source_conv_ids.add(conversation.id)

            existing = note_index.get(conversation.id)
            exporter.export(
                conversation=conversation,
                destination=folder,
                dry_run=dry_run,
                overwrite=overwrite,
                existing=existing,  # new parameter
            )
            processed += 1
        except Exception as e:
            logger.error("Failed: %s - %s", json_path.name, e)
            failed += 1

    # archive orphans using direct ID operations
    if archive_deleted and not dry_run:
        for conv_id, note_info in note_index.items():
            if conv_id not in source_conv_ids:
                if exporter.move_note_to_archive_by_id(note_info.note_id, folder):
                    logger.info("Archived: %s", conv_id)

    return 1 if failed > 0 else 0
```

### apple_notes.py

The `export()` method gains an optional `existing: Optional[NoteInfo]` parameter:

```python
def export(
    self,
    conversation: Conversation,
    destination: str,
    dry_run: bool = False,
    overwrite: bool = True,
    existing: Optional[NoteInfo] = None,  # new
) -> None:
```

When `existing` is provided:

- Uses `existing.note_id` for direct operations
- Uses `existing.last_message_id` to determine if append is needed
- Skips the per-conversation `read_note_body()` call

## Complexity Analysis

| Operation                      | Before                   | After              |
| ------------------------------ | ------------------------ | ------------------ |
| Initial scan                   | -                        | O(M) calls         |
| Per-conversation lookup        | O(M) iterations          | O(1) dict lookup   |
| Update/append                  | O(M) iterations          | O(1) by ID         |
| Archive                        | O(M) iterations/orphan   | O(1) by ID         |
| **Total for N convs, M notes** | **O(N×M)**               | **O(M) + O(N)**    |

For 200 conversations and 200 existing notes:

- Before: ~40,000 iterations across AppleScript calls
- After: ~400 direct AppleScript calls

## Migration

Existing functions that scan by conversation_id (`read_note_body`, `append_to_note`, `move_note_to_archive`) can be deprecated but kept for backwards compatibility or as fallbacks.

## Testing

1. Verify `list_note_ids` returns correct IDs
2. Verify `read_note_body_by_id` reads correct note
3. Verify `scan_folder_notes` builds correct index
4. Verify sync with empty folder (all creates)
5. Verify sync with existing notes (updates/appends)
6. Verify archive operation moves correct orphans
7. Performance test with 200+ conversations
