"""e2e integration tests with real Apple Notes."""

# pylint: disable=redefined-outer-name

import json
import subprocess
import uuid
from collections.abc import Generator
from pathlib import Path

import pytest

from chatgpt2applenotes import main
from chatgpt2applenotes.exporters.apple_notes import AppleNotesExporter

PARENT_FOLDER = "Test"


def ensure_parent_folder() -> None:
    """ensures parent Test folder exists in Apple Notes."""
    applescript = f"""
tell application "Notes"
    if not (exists folder "{PARENT_FOLDER}") then
        make new folder with properties {{name:"{PARENT_FOLDER}"}}
    end if
end tell
"""
    subprocess.run(["osascript", "-e", applescript], capture_output=True, check=False)


def cleanup_subfolder(subfolder: str) -> None:
    """deletes subfolder from parent Test folder in Apple Notes."""
    applescript = f"""
tell application "Notes"
    if exists folder "{subfolder}" of folder "{PARENT_FOLDER}" then
        delete folder "{subfolder}" of folder "{PARENT_FOLDER}"
    end if
end tell
"""
    subprocess.run(["osascript", "-e", applescript], capture_output=True, check=False)


@pytest.fixture
def test_folder() -> Generator[str, None, None]:
    """creates unique subfolder under Test for each test run."""
    ensure_parent_folder()
    subfolder = uuid.uuid4().hex[:8]
    # returns path-like string for the exporter to use
    # the exporter will need to handle "Test/subfolder" format
    folder_path = f"{PARENT_FOLDER}/{subfolder}"
    yield folder_path
    cleanup_subfolder(subfolder)


@pytest.mark.skipif(
    subprocess.run(
        ["osascript", "-e", 'tell application "Notes" to return name'],
        capture_output=True,
        check=False,
    ).returncode
    != 0,
    reason="Apple Notes not available",
)
class TestAppleNotesE2E:
    """e2e tests requiring Apple Notes."""

    def test_sync_creates_note(self, tmp_path: Path, test_folder: str) -> None:
        """syncing a conversation creates a note in Apple Notes."""
        conv_id = str(uuid.uuid4())
        conv = {
            "id": conv_id,
            "title": "E2E Test Conversation",
            "create_time": 1234567890.0,
            "update_time": 1234567890.0,
            "mapping": {
                "msg1": {
                    "message": {
                        "id": "msg-1",
                        "author": {"role": "user"},
                        "create_time": 1234567890.0,
                        "content": {"content_type": "text", "parts": ["Hello"]},
                    }
                }
            },
        }
        json_path = tmp_path / "conversation.json"
        json_path.write_text(json.dumps(conv), encoding="utf-8")

        result = main([str(json_path), test_folder])

        assert result == 0

        # verifies note exists
        exporter = AppleNotesExporter(target="notes")
        body = exporter.read_note_body(test_folder, conv_id)
        assert body is not None
        assert "Hello" in body
        assert f"{conv_id}:" in body

    def test_sync_appends_new_messages(self, tmp_path: Path, test_folder: str) -> None:
        """syncing again appends only new messages."""
        conv_id = str(uuid.uuid4())

        # first sync with one message
        conv1 = {
            "id": conv_id,
            "title": "Append Test",
            "create_time": 1234567890.0,
            "update_time": 1234567890.0,
            "mapping": {
                "msg1": {
                    "message": {
                        "id": "msg-1",
                        "author": {"role": "user"},
                        "create_time": 1234567890.0,
                        "content": {"content_type": "text", "parts": ["First"]},
                    }
                }
            },
        }
        json_path = tmp_path / "conversation.json"
        json_path.write_text(json.dumps(conv1), encoding="utf-8")
        main([str(json_path), test_folder])

        # second sync with additional message
        conv2 = {
            "id": conv_id,
            "title": "Append Test",
            "create_time": 1234567890.0,
            "update_time": 1234567895.0,
            "mapping": {
                "msg1": {
                    "message": {
                        "id": "msg-1",
                        "author": {"role": "user"},
                        "create_time": 1234567890.0,
                        "content": {"content_type": "text", "parts": ["First"]},
                    }
                },
                "msg2": {
                    "message": {
                        "id": "msg-2",
                        "author": {"role": "assistant"},
                        "create_time": 1234567895.0,
                        "content": {"content_type": "text", "parts": ["Second"]},
                    }
                },
            },
        }
        json_path.write_text(json.dumps(conv2), encoding="utf-8")
        main([str(json_path), test_folder])

        # verifies both messages present
        exporter = AppleNotesExporter(target="notes")
        body = exporter.read_note_body(test_folder, conv_id)
        assert body is not None
        assert "First" in body
        assert "Second" in body
        # should have updated footer with last message ID
        assert f"{conv_id}:msg-2" in body

    def test_sync_with_overwrite(self, tmp_path: Path, test_folder: str) -> None:
        """--overwrite replaces entire note content."""
        conv_id = str(uuid.uuid4())

        # first sync
        conv1 = {
            "id": conv_id,
            "title": "Overwrite Test",
            "create_time": 1234567890.0,
            "update_time": 1234567890.0,
            "mapping": {
                "msg1": {
                    "message": {
                        "id": "msg-1",
                        "author": {"role": "user"},
                        "create_time": 1234567890.0,
                        "content": {"content_type": "text", "parts": ["Original"]},
                    }
                }
            },
        }
        json_path = tmp_path / "conversation.json"
        json_path.write_text(json.dumps(conv1), encoding="utf-8")
        main([str(json_path), test_folder])

        # second sync with different content and --overwrite
        conv2 = {
            "id": conv_id,
            "title": "Overwrite Test",
            "create_time": 1234567890.0,
            "update_time": 1234567895.0,
            "mapping": {
                "msg1": {
                    "message": {
                        "id": "msg-new",
                        "author": {"role": "user"},
                        "create_time": 1234567895.0,
                        "content": {"content_type": "text", "parts": ["Replaced"]},
                    }
                }
            },
        }
        json_path.write_text(json.dumps(conv2), encoding="utf-8")
        main([str(json_path), test_folder, "--overwrite"])

        # verifies old content replaced
        exporter = AppleNotesExporter(target="notes")
        body = exporter.read_note_body(test_folder, conv_id)
        assert body is not None
        assert "Replaced" in body

    def test_archive_deleted(self, tmp_path: Path, test_folder: str) -> None:
        """--archive-deleted moves orphaned notes to Archive."""
        # uses UUID format to match list_note_conversation_ids regex pattern
        conv_id_keep = str(uuid.uuid4())
        conv_id_delete = str(uuid.uuid4())

        # creates two notes
        for conv_id, title in [
            (conv_id_keep, "Keep"),
            (conv_id_delete, "Delete"),
        ]:
            conv = {
                "id": conv_id,
                "title": title,
                "create_time": 1234567890.0,
                "update_time": 1234567890.0,
                "mapping": {
                    "msg1": {
                        "message": {
                            "id": "msg-1",
                            "author": {"role": "user"},
                            "create_time": 1234567890.0,
                            "content": {"content_type": "text", "parts": ["Test"]},
                        }
                    }
                },
            }
            json_path = tmp_path / f"{title}.json"
            json_path.write_text(json.dumps(conv), encoding="utf-8")
            main([str(json_path), test_folder])

        # syncs with only one conversation + archive-deleted
        keep_conv = {
            "id": conv_id_keep,
            "title": "Keep",
            "create_time": 1234567890.0,
            "update_time": 1234567890.0,
            "mapping": {
                "msg1": {
                    "message": {
                        "id": "msg-1",
                        "author": {"role": "user"},
                        "create_time": 1234567890.0,
                        "content": {"content_type": "text", "parts": ["Test"]},
                    }
                }
            },
        }
        json_path = tmp_path / "keep_only.json"
        json_path.write_text(json.dumps(keep_conv), encoding="utf-8")
        main([str(json_path), test_folder, "--archive-deleted"])

        # verifies kept note still in main folder
        exporter = AppleNotesExporter(target="notes")
        body = exporter.read_note_body(test_folder, conv_id_keep)
        assert body is not None

        # verifies deleted note moved to Archive (not in main folder)
        body = exporter.read_note_body(test_folder, conv_id_delete)
        assert body is None  # should be moved to Archive
