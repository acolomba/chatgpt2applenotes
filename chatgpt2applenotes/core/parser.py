"""Parser for ChatGPT OpenAPI JSON format (ported from TypeScript)."""

from typing import Any

from chatgpt2applenotes.core.models import Author, Conversation, Message


def process_conversation(json_data: dict[str, Any]) -> Conversation:
    """
    Process a ChatGPT conversation from OpenAPI JSON format.

    Direct port of processConversation from chatgpt-exporter/src/api.ts

    Args:
        json_data: Raw conversation JSON from OpenAPI

    Returns:
        Processed Conversation object
    """
    # Extract basic conversation metadata
    conversation_id = json_data.get("id", "")
    title = json_data.get("title", "Untitled")
    create_time = json_data.get("create_time", 0.0)
    update_time = json_data.get("update_time", 0.0)

    # Process messages from mapping
    messages = _extract_messages(json_data.get("mapping", {}))

    return Conversation(
        id=conversation_id,
        title=title,
        create_time=create_time,
        update_time=update_time,
        messages=messages,
    )


def _extract_messages(mapping: dict[str, Any]) -> list[Message]:
    """Extract and order messages from conversation mapping."""
    messages = []

    for node_id, node in mapping.items():
        message_data = node.get("message")
        if not message_data:
            continue

        # Skip messages without content
        content = message_data.get("content")
        if not content:
            continue

        author_data = message_data.get("author", {})
        author = Author(
            role=author_data.get("role", "unknown"),
            name=author_data.get("name"),
            metadata=author_data.get("metadata", {}),
        )

        message = Message(
            id=message_data.get("id", node_id),
            author=author,
            create_time=message_data.get("create_time", 0.0),
            content=content,
            metadata=message_data.get("metadata", {}),
        )

        messages.append(message)

    # Sort by create_time (TypeScript sorts by default)
    messages.sort(key=lambda m: m.create_time)

    return messages
