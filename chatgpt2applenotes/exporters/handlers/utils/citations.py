"""citation rendering utilities for ChatGPT content references."""

import html
from typing import Any, Optional


def render_citations(text: str, metadata: Optional[dict[str, Any]]) -> str:
    """
    replaces citation markers with attribution links.

    Args:
        text: HTML text with citation markers
        metadata: message metadata containing content_references

    Returns:
        text with citations replaced by links
    """
    if not metadata:
        return text

    content_refs = metadata.get("content_references", [])
    if not content_refs:
        return text

    for ref in content_refs:
        matched_text = ref.get("matched_text", "")
        # skips empty or whitespace-only markers
        if not matched_text or matched_text.isspace():
            continue

        items = ref.get("items", [])
        if not items:
            # no items, just remove the marker
            text = text.replace(matched_text, "")
            continue

        # builds links from items and supporting_websites
        links = []
        for item in items:
            url = item.get("url", "")
            attribution = item.get("attribution", "")
            if url and attribution:
                escaped_url = html.escape(url)
                escaped_attr = html.escape(attribution)
                links.append(f'<a href="{escaped_url}">{escaped_attr}</a>')

            # adds supporting websites
            for support in item.get("supporting_websites", []):
                s_url = support.get("url", "")
                s_attr = support.get("attribution", "")
                if s_url and s_attr:
                    escaped_url = html.escape(s_url)
                    escaped_attr = html.escape(s_attr)
                    links.append(f'<a href="{escaped_url}">{escaped_attr}</a>')

        if links:
            replacement = "(" + ", ".join(links) + ")"
            text = text.replace(matched_text, replacement)
        else:
            text = text.replace(matched_text, "")

    return text
