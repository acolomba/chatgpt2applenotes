# Apple Notes Exporter Refactoring Design

## Problem

`chatgpt2applenotes/exporters/apple_notes.py` has grown to 1,027 lines, requiring a `pylint: disable=too-many-lines` comment. The file mixes three distinct responsibilities:

1. AppleScript operations (subprocess calls to `osascript`)
2. HTML/Markdown rendering (markdown-it customization, content type handlers)
3. Export orchestration (file vs notes target, sync logic)

## Goal

Split into three focused modules to reduce complexity while preserving the public API. Keep an eye out for reuse opportunities (e.g., renderer could support other export targets).

## Design

### Module Structure

```text
exporters/
├── __init__.py           # (unchanged)
├── base.py               # (unchanged)
├── apple_notes.py        # main exporter class (~250 lines)
├── applescript.py        # Apple Notes AppleScript operations (~350 lines)
└── html_renderer.py      # markdown/HTML rendering (~400 lines)
```

### Dependency Flow

```text
apple_notes.py
    ├── imports from applescript.py
    ├── imports from html_renderer.py
    └── imports from base.py (Exporter)
```

No circular dependencies. `applescript.py` and `html_renderer.py` are independent leaf modules.

---

### `applescript.py` -- AppleScript Operations

Encapsulates all Apple Notes interactions via `osascript` subprocess calls.

#### Public API

```python
def get_folder_ref(folder_name: str) -> str
    """generates AppleScript folder reference for given path."""

def get_folder_create_script(folder_name: str) -> str
    """generates AppleScript to create folder (and parent if nested)."""

def write_note(
    folder_name: str,
    conversation_id: str,
    html_content: str,
    overwrite: bool,
    image_files: list[str],
) -> None
    """writes or updates note in Apple Notes."""

def read_note_body(folder: str, conversation_id: str) -> Optional[str]
    """reads note body from Apple Notes by conversation ID."""

def append_to_note(folder: str, conversation_id: str, html_content: str) -> bool
    """appends HTML content to existing note."""

def list_note_conversation_ids(folder: str) -> list[str]
    """lists all conversation IDs from notes in folder."""

def move_note_to_archive(folder: str, conversation_id: str) -> bool
    """moves note to Archive subfolder."""
```

#### Private Helpers

```python
def _parse_folder_path(folder_name: str) -> tuple[str, Optional[str]]
    """parses folder path into (parent, subfolder)."""

def _escape_applescript(value: str) -> str
    """escapes string for AppleScript embedding."""

def _run_applescript(script: str) -> subprocess.CompletedProcess[str]
    """executes AppleScript via osascript."""
```

#### Design Notes

- Functions (not a class) since operations are stateless
- All AppleScript string escaping centralized in `_escape_applescript()`
- Temp file creation/cleanup for HTML and images handled internally
- Image deduplication workaround for Apple Notes 4.10-4.11 bug stays here

---

### `html_renderer.py` -- Markdown/HTML Rendering

Handles all content-to-HTML conversion for Apple Notes format.

#### Public API

```python
class AppleNotesRenderer:
    def render_conversation(self, conversation: Conversation) -> str
        """generates Apple Notes HTML for full conversation."""

    def render_append(self, conversation: Conversation, after_message_id: str) -> str
        """generates HTML for messages after the given message ID."""

    def extract_last_synced_id(self, html: str) -> Optional[str]
        """extracts last-synced message ID from note footer."""
```

#### Private Methods

```python
def _markdown_to_apple_notes(self, markdown: str) -> str
    """converts markdown to Apple Notes HTML format."""

def _add_block_spacing(self, html: str) -> str
    """adds <div><br></div> between adjacent block elements."""

def _protect_latex(self, text: str) -> tuple[str, list[str]]
    """replaces LaTeX with placeholders to protect from markdown processing."""

def _restore_latex(self, text: str, matches: list[str]) -> str
    """restores LaTeX from placeholders."""

def _render_message_content(self, message: Message) -> str
    """renders message content to Apple Notes HTML."""

def _render_user_content(self, message: Message) -> str
    """renders user message content (escaped HTML, no markdown)."""

def _render_text_content(self, message: Message) -> str
def _render_multimodal_content(self, content: dict, escape_text: bool = False) -> str
def _render_code_content(self, message: Message) -> str
def _render_execution_output(self, message: Message) -> str
def _render_tether_quote(self, message: Message) -> str
def _render_tether_browsing_display(self, message: Message) -> str

def _get_author_label(self, message: Message) -> str
    """returns friendly author label."""

def _tool_message_has_visible_content(self, message: Message) -> bool
    """checks if tool message has user-visible content."""
```

#### Constants

```python
LATEX_PATTERN = re.compile(...)
FOOTNOTE_PATTERN = re.compile(...)
```

#### Design Notes

- Class (not functions) because it benefits from holding markdown-it instance
- `extract_last_synced_id()` belongs here since it parses the HTML format this renderer produces
- `_get_author_label()` and `_tool_message_has_visible_content()` move here since they're about rendering decisions

---

### `apple_notes.py` -- Main Exporter (Slimmed Down)

Orchestration layer that coordinates rendering and AppleScript operations.

#### Public API (Unchanged)

```python
class AppleNotesExporter(Exporter):
    def __init__(
        self,
        target: Literal["file", "notes"] = "file",
        cc_dir: Optional[Path] = None,
    ) -> None

    def export(
        self,
        conversation: Conversation,
        destination: str,
        dry_run: bool = False,
        overwrite: bool = True,
    ) -> None

    # delegated to applescript module (kept as methods for backward compatibility)
    def read_note_body(self, folder: str, conversation_id: str) -> Optional[str]
    def append_to_note(self, folder: str, conversation_id: str, html_content: str) -> bool
    def list_note_conversation_ids(self, folder: str) -> list[str]
    def move_note_to_archive(self, folder: str, conversation_id: str) -> bool
```

#### Internal Structure

```python
class AppleNotesExporter(Exporter):
    def __init__(self, ...):
        self.target = target
        self.cc_dir = cc_dir
        self._renderer = AppleNotesRenderer()

    def export(self, ...):
        # dispatches to _export_to_file() or _export_to_notes()

    def _export_to_file(self, ...):
        # generates HTML via renderer, writes to file

    def _export_to_notes(self, ...):
        # handles sync logic, calls applescript.write_note()

    def _save_cc_copy(self, ...):
        # debug copy feature

    # thin wrappers for backward compatibility
    def read_note_body(self, folder, conversation_id):
        return applescript.read_note_body(folder, conversation_id)
    # ... etc
```

#### Design Notes

- Public interface unchanged -- `sync.py` and tests need no modifications
- AppleScript methods become thin wrappers delegating to `applescript` module
- Holds `AppleNotesRenderer` instance for HTML generation
- Image extraction (`_generate_html_with_images`, `_save_image_to_file`, `_convert_image_to_png_data_url`) stays here since it's export-target-specific

---

## Migration Plan

1. Create `applescript.py` with functions extracted from `AppleNotesExporter`
2. Create `html_renderer.py` with `AppleNotesRenderer` class
3. Update `apple_notes.py` to import and delegate to new modules
4. Remove `# pylint: disable=too-many-lines` comment
5. Run tests to verify no regressions
6. Update test imports if needed (unlikely since public API unchanged)

## Test Impact

- Existing tests should pass without modification (public API preserved)
- New unit tests can be added for `applescript.py` and `html_renderer.py` in isolation
- Mock boundaries become cleaner (can mock `applescript` module instead of subprocess)

## Estimated Line Counts

| Module | Lines |
| ------ | ----- |
| `apple_notes.py` | ~250 |
| `applescript.py` | ~350 |
| `html_renderer.py` | ~400 |
| **Total** | ~1,000 |

All modules well under pylint's default 1,000 line limit.
