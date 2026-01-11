"""Data models for ChatGPT conversations (ported from TypeScript)."""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Author:
    """Message author information."""

    role: str  # "user", "assistant", "system"
    name: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MessageContent:
    """Message content structure."""

    content_type: str
    parts: list[str]


@dataclass
class Message:
    """Individual message in a conversation."""

    id: str
    author: Author
    create_time: float
    content: dict[str, Any]  # Flexible for various content types
    metadata: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Conversation:
    """Complete conversation structure."""

    id: str
    title: str
    create_time: float
    update_time: float
    messages: list[Message]
    metadata: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}
