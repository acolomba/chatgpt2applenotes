"""progress and output handling for sync operations."""

from typing import Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
)


class ProgressHandler:  # pylint: disable=too-few-public-methods
    """handles progress display and output for sync operations."""

    def __init__(self, quiet: bool = False, show_progress: bool = False) -> None:
        self.quiet = quiet
        self.show_progress = show_progress
        self._console = Console(stderr=True)
        self._progress: Optional[Progress] = None
        self._task_id: Optional[TaskID] = None
        self._total = 0

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

    def start_discovery(self) -> None:
        """starts spinner for discovery phase."""
        if not self.show_progress:
            return

        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self._console,
            transient=True,
        )
        self._progress.start()
        self._task_id = self._progress.add_task(
            "Discovering conversations...", total=None
        )

    def start_scanning(self) -> None:
        """starts spinner for note scanning phase."""
        if not self.show_progress:
            return

        # stops discovery spinner if running
        if self._progress is not None:
            self._progress.stop()

        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self._console,
            transient=True,
        )
        self._progress.start()
        self._task_id = self._progress.add_task(
            "Scanning existing notes...", total=None
        )

    def set_total(self, total: int) -> None:
        """switches from spinner to determinate progress bar."""
        if not self.show_progress:
            return

        # stops spinner
        if self._progress is not None:
            self._progress.stop()

        # starts determinate progress bar
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("- {task.fields[title]}"),
            console=self._console,
            transient=True,
        )
        self._progress.start()
        self._task_id = self._progress.add_task("Syncing", total=total, title="")
        self._total = total

    def adjust_total(self, delta: int) -> None:
        """increases total when multi-conversation file found."""
        if not self.show_progress or self._progress is None or self._task_id is None:
            return

        self._total += delta
        self._progress.update(self._task_id, total=self._total)

    def update(self, title: str) -> None:
        """advances progress by 1 and updates current title."""
        if not self.show_progress or self._progress is None or self._task_id is None:
            return

        self._progress.update(self._task_id, advance=1, title=title)

    def log_error(self, message: str) -> None:
        """prints error message (always shown, even in quiet mode)."""
        self._console.print(f"[red]ERROR:[/red] {message}")

    def log_info(self, message: str) -> None:
        """prints info message (only when not quiet and progress disabled)."""
        if self.quiet or self.show_progress:
            return

        self._console.print(message)

    def finish(self, processed: int, failed: int) -> None:
        """stops progress and prints summary unless quiet."""
        if self._progress is not None:
            self._progress.stop()
            self._progress = None

        if self.quiet:
            return

        total = processed + failed
        self._console.print(
            f"Processed {total} conversation(s): {processed} synced, {failed} failed"
        )
