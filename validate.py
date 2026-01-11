#!/usr/bin/env python3
"""Validation script to compare generated HTML with reference."""

import filecmp
import json
import re
import sys
from pathlib import Path

from chatgpt2applenotes.core.parser import process_conversation
from chatgpt2applenotes.exporters.html import HTMLExporter


def validate_file(
    json_path: Path, reference_html: Path, output_dir: Path
) -> tuple[bool, str]:
    """
    Validate single file against reference.

    Returns:
        (success, message) tuple
    """
    try:
        # parses JSON
        with open(json_path, encoding="utf-8") as f:
            json_data = json.load(f)

        conversation = process_conversation(json_data)

        # exports to output directory
        exporter = HTMLExporter()
        exporter.export(conversation, str(output_dir), dry_run=False, overwrite=True)

        # determines output filename (matching HTMLExporter logic)
        safe_title = re.sub(r"[^\w\s-]", "", conversation.title)
        safe_title = re.sub(r"[-\s]+", "_", safe_title).strip("_")
        output_file = output_dir / f"ChatGPT-{safe_title}.html"

        # compares files
        if not output_file.exists():
            return False, f"Output file not created: {output_file}"

        if not reference_html.exists():
            return False, f"Reference file not found: {reference_html}"

        if filecmp.cmp(output_file, reference_html, shallow=False):
            return True, "✓ Files match exactly"
        return False, "✗ Files differ"

    except (OSError, json.JSONDecodeError) as e:
        return False, f"Error: {e}"


def main() -> None:
    """Runs validation on sample files."""
    sample_files = [
        "ChatGPT-Freezing_Rye_Bread",
        "ChatGPT-Fix_libflac_error",
        "ChatGPT-Authentication_session_explained",
        "ChatGPT-Best_Non-Alcoholic_Beer",
        "ChatGPT-Wegovy_and_Glucose_Stabilization",
    ]

    json_dir = Path("/Users/acolomba/Downloads/chatgpt-export-json")
    reference_dir = Path("/Users/acolomba/Downloads/chatgpt-export-html")
    output_dir = Path("output/html")
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []

    for basename in sample_files:
        json_path = json_dir / f"{basename}.json"
        reference_html = reference_dir / f"{basename}.html"

        print(f"\nValidating {basename}...")
        success, message = validate_file(json_path, reference_html, output_dir)
        results.append((basename, success, message))
        print(f"  {message}")

    # summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    for basename, _success, message in results:
        print(f"{basename}: {message}")

    print(f"\n{passed}/{total} files match exactly")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
