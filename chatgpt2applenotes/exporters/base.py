"""base exporter interface."""

from abc import ABC, abstractmethod

from chatgpt2applenotes.core.models import Conversation


class Exporter(ABC):  # pylint: disable=too-few-public-methods
    """abstract base class for conversation exporters."""

    @abstractmethod
    def export(
        self,
        conversation: Conversation,
        destination: str,
        dry_run: bool = False,
        overwrite: bool = False,
    ) -> None:
        """
        Export a conversation to the destination.

        Args:
            conversation: The conversation to export
            destination: Where to write the export (interpretation varies by exporter)
            dry_run: If True, don't actually write anything
            overwrite: If True, overwrite existing content
        """
        ...  # pylint: disable=unnecessary-ellipsis
