"""Heading-path targeting, the escape hatch for patching skills that have no anchors.

Heading paths are inherently unstable across upstream versions, so every heading
patch must pin the target section's content hash. When upstream edits that
section the build fails and names the new hash, forcing a human to re-read the
change instead of silently patching something else.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from skillforge.errors import PatchError

_ATX_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<title>.+?)\s*#*\s*$")
_FENCE_RE = re.compile(r"^\s*(?P<fence>```+|~~~+)")


@dataclass
class Section:
    level: int
    title: str
    path: tuple[str, ...]
    start: int
    body_start: int
    end: int

    def text(self, body: str) -> str:
        return body[self.start : self.end]

    def hash(self, body: str) -> str:
        digest = hashlib.sha256(self.text(body).encode("utf-8")).hexdigest()
        return f"sha256:{digest}"


def parse_sections(body: str) -> list[Section]:
    """Every ATX heading, with its span running to the next heading of equal or higher level."""
    lines = body.splitlines(keepends=True)
    offsets: list[int] = []
    cursor = 0
    for line in lines:
        offsets.append(cursor)
        cursor += len(line)

    found: list[tuple[int, int, str, int]] = []  # line index, level, title, char offset
    fence: str | None = None
    for index, line in enumerate(lines):
        fence_match = _FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group("fence")[0] * 3
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
            continue
        if fence is not None:
            continue
        heading = _ATX_RE.match(line)
        if heading:
            found.append(
                (
                    index,
                    len(heading.group("hashes")),
                    heading.group("title").strip(),
                    offsets[index],
                )
            )

    sections: list[Section] = []
    stack: list[str] = []
    for position, (index, level, title, offset) in enumerate(found):
        del stack[level - 1 :]
        stack.append(title)
        end = len(body)
        for other_index, other_level, _, other_offset in found[position + 1 :]:
            del other_index
            if other_level <= level:
                end = other_offset
                break
        sections.append(
            Section(
                level=level,
                title=title,
                path=tuple(stack),
                start=offset,
                body_start=offset + len(lines[index]),
                end=end,
            )
        )
    return sections


def find_section(body: str, selector: str, origin: str) -> Section:
    """Resolve `A > B > C` (or a bare title) to exactly one section."""
    wanted = tuple(part.strip() for part in selector.split(">"))
    sections = parse_sections(body)
    matches = [s for s in sections if s.path[-len(wanted) :] == wanted]
    if not matches:
        available = "\n  ".join(" > ".join(s.path) for s in sections) or "(no headings)"
        raise PatchError(
            f"{origin}: heading `{selector}` not found. Available headings:\n  {available}"
        )
    if len(matches) > 1:
        candidates = "\n  ".join(" > ".join(s.path) for s in matches)
        raise PatchError(
            f"{origin}: heading `{selector}` is ambiguous, it matches:\n  {candidates}\n"
            "Qualify it with a full `Parent > Child` path."
        )
    return matches[0]
