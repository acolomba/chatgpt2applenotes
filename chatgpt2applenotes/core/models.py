"""Data models for ChatGPT conversations (ported from TypeScript)."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Author:
    """Message author information."""

    role: str  # "user", "assistant", "system"
    name: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


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
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    """Complete conversation structure."""

    id: str
    title: str
    create_time: float
    update_time: float
    messages: list[Message]
    metadata: dict[str, Any] = field(default_factory=dict)
