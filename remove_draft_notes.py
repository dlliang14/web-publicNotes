#!/usr/bin/env python3
"""
Remove markdown files with 'draft: true' frontmatter from the content directory.
This script is used in CI/CD to prevent draft notes from being included in the published site.
"""

import os
import re
from pathlib import Path


def has_draft_frontmatter(file_path):
    """Check if a markdown file has 'draft: true' in its frontmatter."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Check if draft: true exists in the frontmatter (between --- markers)
            if content.startswith("---"):
                # Find the closing --- of frontmatter
                match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
                if match:
                    frontmatter = match.group(1)
                    return "draft: true" in frontmatter
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return False


def main():
    content_dir = Path("content")
    if not content_dir.exists():
        print("content directory not found")
        return

    removed_files = []
    for md_file in content_dir.glob("*.md"):
        if has_draft_frontmatter(md_file):
            try:
                md_file.unlink()
                removed_files.append(md_file.name)
                print(f"Removed: {md_file.name}")
            except Exception as e:
                print(f"Error removing {md_file.name}: {e}")

    if removed_files:
        print(f"\nSuccessfully removed {len(removed_files)} draft notes:")
        for name in removed_files:
            print(f"  - {name}")
    else:
        print("No draft notes found to remove")


if __name__ == "__main__":
    main()
