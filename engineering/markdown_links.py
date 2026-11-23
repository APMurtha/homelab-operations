#!/usr/bin/env python3
import re
import sys
from pathlib import Path
from typing import Iterable, List, NamedTuple, Sequence
from urllib.parse import unquote, urlparse

LINK_PATTERN = re.compile(r'!?(?<!\\)\[([^\]]*)\]\(([^)]+)\)')
FENCE_PATTERN = re.compile(r'^(?P<indent>[ \t]{0,3})(?P<fence>`{3,}|~{3,})(?P<rest>.*)$')
MARKDOWN_SUFFIXES = {'.md', '.markdown', '.mdown', '.mkd'}


class BrokenLink(NamedTuple):
    source_path: str
    line_number: int
    destination: str
    resolved_path: str


def iter_markdown_files(paths: Sequence[str]) -> Iterable[Path]:
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            for child in sorted(path.rglob('*')):
                if child.is_file() and child.suffix.lower() in MARKDOWN_SUFFIXES:
                    yield child
        elif path.is_file() and path.suffix.lower() in MARKDOWN_SUFFIXES:
            yield path


def normalize_destination(destination: str) -> str:
    value = destination.strip()
    if value.startswith('<') and value.endswith('>') and len(value) >= 2:
        value = value[1:-1].strip()
    return value


def is_ignored_destination(destination: str) -> bool:
    if not destination or destination.startswith('#'):
        return True
    parsed = urlparse(destination)
    if parsed.scheme or parsed.netloc:
        return parsed.scheme in {'http', 'https', 'mailto'} or bool(parsed.netloc)
    return False


def split_destination(destination: str) -> tuple[str, str]:
    return destination.split('#', 1) if '#' in destination else (destination, '')


def resolve_target(source_file: Path, destination: str) -> Path:
    relative_path, _fragment = split_destination(destination)
    decoded = unquote(relative_path)
    return (source_file.parent / decoded).resolve()


def fence_state_transition(line: str, active_fence: tuple[str, int] | None) -> tuple[str, int] | None:
    match = FENCE_PATTERN.match(line)
    if not match:
        return active_fence
    fence = match.group('fence')
    fence_char = fence[0]
    fence_length = len(fence)
    if active_fence is None:
        return (fence_char, fence_length)
    active_char, active_length = active_fence
    if fence_char == active_char and fence_length >= active_length and not match['rest'].strip(' \t'):
        return None
    return active_fence


def find_broken_links_in_file(path: Path) -> List[BrokenLink]:
    broken: List[BrokenLink] = []
    active_fence: tuple[str, int] | None = None
    with path.open('r', encoding='utf-8') as handle:
        for line_number, line in enumerate(handle, start=1):
            next_fence = fence_state_transition(line, active_fence)
            if active_fence is not None:
                active_fence = next_fence
                continue
            if next_fence is not None:
                active_fence = next_fence
                continue
            for match in LINK_PATTERN.finditer(line):
                destination = normalize_destination(match.group(2))
                if is_ignored_destination(destination):
                    continue
                relative_path, _fragment = split_destination(destination)
                if not relative_path:
                    continue
                target = resolve_target(path, destination)
                if not target.exists():
                    broken.append(BrokenLink(str(path), line_number, destination, str(target)))
    return broken


def collect_broken_links(paths: Sequence[str]) -> List[BrokenLink]:
    broken: List[BrokenLink] = []
    seen = set()
    for markdown_file in iter_markdown_files(paths):
        resolved = markdown_file.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        broken.extend(find_broken_links_in_file(resolved))
    broken.sort(key=lambda item: (item.source_path, item.line_number, item.destination))
    return broken


def format_broken_link(entry: BrokenLink) -> str:
    return f'{entry.source_path}:{entry.line_number}: broken relative link: {entry.destination}'


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        print('usage: markdown_links.py PATH [PATH ...]', file=sys.stderr)
        return 2
    broken = collect_broken_links(args)
    for entry in broken:
        print(format_broken_link(entry), file=sys.stderr)
    return 1 if broken else 0


if __name__ == '__main__':
    raise SystemExit(main())
