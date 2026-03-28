#!/usr/bin/env python3
"""
Flatten files from non-hidden subdirectories under content into the content root.
This is used in CI/CD because Foam can resolve wikilinks across folders,
but the frontend expects published notes at the content root.
"""

import argparse
import os
import shutil
from pathlib import Path


def iter_files_to_move(content_dir):
    """Yield files from non-hidden subdirectories under the content directory."""
    for child in content_dir.iterdir():
        if not child.is_dir() or child.name.startswith("."):
            continue

        for current_root, dirnames, filenames in os.walk(child):
            dirnames[:] = [name for name in dirnames if not name.startswith(".")]

            for filename in filenames:
                yield Path(current_root) / filename


def collect_move_plan(content_dir):
    """Plan moves and detect filename collisions before making changes."""
    planned_moves = []
    planned_targets = {}
    collisions = {}

    for source in iter_files_to_move(content_dir):
        target = content_dir / source.name
        collision_paths = []

        if target.exists():
            collision_paths.append(target)

        if target in planned_targets:
            collision_paths.append(planned_targets[target])

        if collision_paths:
            collisions.setdefault(target, set()).update(collision_paths)
            collisions[target].add(source)
            continue

        planned_moves.append((source, target))
        planned_targets[target] = source

    return planned_moves, collisions


def remove_empty_directories(content_dir):
    """Remove emptied non-hidden directories after files are moved."""
    removed_dirs = []
    directories = [
        path
        for path in content_dir.rglob("*")
        if path.is_dir() and not path.name.startswith(".")
    ]

    for directory in sorted(
        directories, key=lambda path: len(path.parts), reverse=True
    ):
        try:
            directory.rmdir()
            removed_dirs.append(directory)
        except OSError:
            continue

    return removed_dirs


def find_empty_directories_after_moves(content_dir, planned_moves):
    """Predict which non-hidden directories become empty after the move plan."""
    moved_sources = {source for source, _ in planned_moves}
    empty_dirs = []
    directories = [
        path
        for path in content_dir.rglob("*")
        if path.is_dir() and not path.name.startswith(".")
    ]

    for directory in sorted(
        directories, key=lambda path: len(path.parts), reverse=True
    ):
        remaining_entries = []
        for entry in directory.iterdir():
            if entry.name.startswith("."):
                remaining_entries.append(entry)
                continue

            if entry.is_file() and entry not in moved_sources:
                remaining_entries.append(entry)
                continue

            if entry.is_dir() and entry not in empty_dirs:
                remaining_entries.append(entry)

        if not remaining_entries:
            empty_dirs.append(directory)

    return empty_dirs


def parse_args():
    parser = argparse.ArgumentParser(
        description="Flatten non-hidden content subdirectories into the content root"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show planned moves without modifying files",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    content_dir = Path("content")
    if not content_dir.exists():
        print("content directory not found")
        return 1

    planned_moves, collisions = collect_move_plan(content_dir)

    if collisions:
        print("Filename collisions detected. Resolve them before flattening content:")
        for target, paths in sorted(collisions.items()):
            print(f"  - {target.name}")
            for path in sorted(paths):
                print(f"      {path}")
        return 1

    if not planned_moves:
        print("No files found in non-hidden content subdirectories")
        return 0

    if args.dry_run:
        predicted_removed_dirs = find_empty_directories_after_moves(
            content_dir, planned_moves
        )
        print(f"Dry run: {len(planned_moves)} files would be moved to content root")
        for source, target in planned_moves:
            print(f"Would move: {source} -> {target}")

        if predicted_removed_dirs:
            print(
                f"Dry run: {len(predicted_removed_dirs)} directories would be removed"
            )
            for directory in predicted_removed_dirs:
                print(f"Would remove empty directory: {directory}")
        return 0

    moved_files = []
    for source, target in planned_moves:
        try:
            shutil.move(str(source), str(target))
            moved_files.append(target.name)
            print(f"Moved: {source} -> {target}")
        except Exception as error:
            print(f"Error moving {source} to {target}: {error}")
            return 1

    removed_dirs = remove_empty_directories(content_dir)

    print(f"\nSuccessfully moved {len(moved_files)} files to content root")
    if removed_dirs:
        print(f"Removed {len(removed_dirs)} empty directories")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
