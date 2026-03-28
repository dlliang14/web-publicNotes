from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def is_relative_to(path: Path, other: Path) -> bool:
    try:
        path.relative_to(other)
        return True
    except ValueError:
        return False


def parse_frontmatter(text: str) -> str | None:
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return None

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break

    if end_index is None:
        return None

    return "\n".join(lines[1:end_index])


def has_tag(frontmatter: str, tag_name: str) -> bool:
    in_tags_block = False

    for raw_line in frontmatter.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            if in_tags_block:
                continue
            continue

        if stripped.startswith("tags:"):
            after_colon = stripped[len("tags:") :].strip()
            if after_colon.startswith("[") and after_colon.endswith("]"):
                items = [
                    item.strip().strip("\"'")
                    for item in after_colon[1:-1].split(",")
                    if item.strip()
                ]
                return tag_name in items

            in_tags_block = True
            continue

        if in_tags_block:
            if (
                raw_line.startswith(" ")
                or raw_line.startswith("\t")
                or stripped.startswith("-")
            ):
                if stripped.startswith("-"):
                    value = stripped[1:].strip().strip("\"'")
                    if value == tag_name:
                        return True
                continue

            in_tags_block = False

    return False


def iter_markdown_files(root: Path, target_dir: Path):
    for path in root.rglob("*.md"):
        relative_parts = path.relative_to(root).parts
        if any(part.startswith(".") for part in relative_parts[:-1]):
            continue

        if is_relative_to(path, target_dir):
            continue

        yield path


def move_tagged_notes(
    root: Path,
    target_path: Path,
    tag_name: str,
    dry_run: bool,
    force: bool,
) -> int:
    target_dir = target_path if target_path.is_absolute() else (root / target_path)
    target_dir.mkdir(parents=True, exist_ok=True)

    moved = 0
    skipped = 0

    for path in iter_markdown_files(root, target_dir):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(f"[skip] 编码不是 UTF-8: {path.relative_to(root)}")
            skipped += 1
            continue

        frontmatter = parse_frontmatter(text)
        if not frontmatter or not has_tag(frontmatter, tag_name):
            continue

        destination = target_dir / path.name
        if destination.exists() and destination.resolve() != path.resolve():
            if not force:
                print(f"[skip] 目标已存在: {destination.relative_to(root)}")
                skipped += 1
                continue
            if not dry_run:
                destination.unlink()

        print(f"[move] {path.relative_to(root)} -> {destination.relative_to(root)}")
        moved += 1

        if not dry_run:
            shutil.move(str(path), str(destination))

    print(f"完成: moved={moved}, skipped={skipped}, dry_run={dry_run}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="扫描非隐藏目录中的 Markdown 笔记，将带有指定 tag 的文件移动到目标目录。"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="要扫描的根目录，默认是当前目录。",
    )
    parser.add_argument(
        "--target-path",
        type=Path,
        default=Path("大纲"),
        help="目标目录路径，默认是 大纲。支持相对路径和绝对路径。",
    )
    parser.add_argument(
        "--tag-name",
        default="大纲",
        help="要匹配的 tag 名称，默认是 大纲。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印将要移动的文件，不实际移动。",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="目标文件已存在时覆盖它。",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    return move_tagged_notes(
        root=root,
        target_path=args.target_path,
        tag_name=args.tag_name,
        dry_run=args.dry_run,
        force=args.force,
    )


if __name__ == "__main__":
    raise SystemExit(main())
