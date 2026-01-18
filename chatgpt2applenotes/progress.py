"""progress and output handling for sync operations."""

from typing import Optional

from rich.console import Console
from rich.progress import Progress, TaskID


class ProgressHandler:  # pylint: disable=too-few-public-methods
    """handles progress display and output for sync operations."""

    def __init__(self, quiet: bool = False, show_progress: bool = False) -> None:
        self.quiet = quiet
        self.show_progress = show_progress
        self._console = Console(stderr=True)
        self._progress: Optional[Progress] = None
        self._task_id: Optional[TaskID] = None

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
