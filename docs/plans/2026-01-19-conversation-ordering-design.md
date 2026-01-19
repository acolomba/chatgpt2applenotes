# Conversation Ordering Design

## Goal

Process conversations in `update_time` ascending order so Apple Notes modification timestamps match ChatGPT's ordering.

## Background

- ChatGPT shows conversations sorted by `update_time` (most recent at top)
- Apple Notes sorts notes by modification date (most recent at top)
- Processing conversations oldest-first means the most recently updated conversations get processed last, giving them the newest Apple Notes modification timestamps
- This makes the order in Apple Notes match the order in ChatGPT

## Approach

### Two-Pass Processing

1. **Index pass**: stream-parse all files to build a lightweight index
2. **Sort**: order by `update_time` ascending (oldest first)
3. **Process pass**: export conversations in sorted order

### Index Format

```python
list[tuple[float, Path, int]]  # (update_time, path, index)
```

- `(update_time, path, -1)` for single-conversation dict files (`{ ... }`)
- `(update_time, path, N)` for conversation at index N in list files (`[ ... ]`)

The `-1` sentinel distinguishes JSON structure: dict vs list.

### Streaming with ijson

Use `ijson` for memory-efficient stream parsing during the index pass:

- For dict files `{ ... }`: stream to extract just `update_time`, avoids loading potentially huge conversation content
- For list files `[ ... ]`: stream through each conversation object, extracting `update_time` from each

This is important because most large exports are ZIP files containing many long single-conversation files.

### Processing Order

For the second pass, re-parse files as needed:

- Index `-1`: parse file, use the conversation directly
- Index `>= 0`: parse file, extract `conversations[index]`

List files may be re-parsed multiple times if their conversations interleave with other files in the sorted order. This is acceptable because list files are uncommon.

## Implementation

### Files to Modify

1. **`sync.py`**:
   - Add `build_conversation_index()` function
   - Modify `sync_conversations()` to use index-based processing
   - Remove current filename-based sorting

2. **`pyproject.toml`**:
   - Add `ijson` dependency

### Files Unchanged

- `core/parser.py` - still parses full conversations when needed
- `core/models.py` - no changes
- `exporters/*` - no changes (they receive `Conversation` objects as before)
- `progress.py` - no changes (just gets accurate count earlier)
- `__init__.py` - CLI unchanged

### New Function

```python
def build_conversation_index(files: list[Path]) -> list[tuple[float, Path, int]]:
    """
    stream-parses all files to build index of (update_time, path, index) tuples.

    - peeks first non-whitespace char to detect structure
    - uses ijson to extract only update_time from each conversation
    - returns unsorted list (caller should sort)
    """
```

### Modified Flow

Current:

```text
discover files -> sort by filename -> process each file sequentially
```

New:

```text
discover files -> build index (streaming) -> sort by update_time -> process in sorted order
```

### Progress Bar Benefit

The index pass gives us an exact conversation count upfront, enabling accurate progress bar initialization.

## Error Handling

### Index Building Errors

- Malformed JSON: log warning, skip file, continue indexing
- Missing `update_time` field: log warning, skip that conversation
- I/O errors: log warning, skip file

### Processing Errors (Unchanged)

- If a conversation fails during export, log error, continue with next
- Partial failures result in exit code 1

## Edge Cases

| Case                               | Behavior                                                        |
| ---------------------------------- | --------------------------------------------------------------- |
| Empty export (no conversations)    | Index is empty, nothing to process, exit 0                      |
| All files fail indexing            | Empty index, log summary warning, exit 0                        |
| Duplicate `update_time` values     | Stable sort preserves discovery order                           |
| ZIP with nested directories        | File discovery unchanged, indexing handles all discovered files |

## Performance

- Index pass is I/O-bound (streaming), minimal memory
- For N conversations across M files: M file reads for indexing + N file reads for processing
- Re-reads for interleaved list files are rare and acceptable

## Trade-offs

- **Re-parse list files when interleaved**: accepted because list files are uncommon
- **Two-pass vs single-pass**: required to sort by `update_time` without holding all conversations in memory
- **ijson dependency**: necessary for memory-efficient streaming of large files
