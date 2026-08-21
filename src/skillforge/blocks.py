"""Anchors: `block` regions and `point` insertion sites inside a skill body.

Anchors are the stable contract a base skill offers to whoever imports it. They
are HTML comments, so a base skill renders as ordinary markdown everywhere and
stays usable without skillforge.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from skillforge.errors import SkillError
from skillforge.expr import evaluate

BLOCK_OPEN_RE = re.compile(
    r"<!--\s*skillforge:block\s+id=(?P<id>[A-Za-z0-9_-]+)"
    r"(?:\s+when=(?P<q>[\"'])(?P<when>.*?)(?P=q))?\s*-->"
)
BLOCK_CLOSE_RE = re.compile(r"<!--\s*/skillforge:block\s*-->")
POINT_RE = re.compile(r"<!--\s*skillforge:point\s+id=(?P<id>[A-Za-z0-9_-]+)\s*-->")
_ANY_MARKER_RE = re.compile(r"<!--\s*/?skillforge:(?P<kind>[a-z]+)(?P<rest>[^>]*)-->")


@dataclass
class Block:
    id: str
    when: str | None
    open_start: int
    open_end: int
    close_start: int
    close_end: int

    @property
    def inner(self) -> tuple[int, int]:
        return (self.open_end, self.close_start)

    @property
    def outer(self) -> tuple[int, int]:
        return (self.open_start, self.close_end)


@dataclass
class Point:
    id: str
    start: int
    end: int


@dataclass
class Anchors:
    blocks: dict[str, Block]
    points: dict[str, Point]


def parse_anchors(body: str, origin: str) -> Anchors:
    """Locate every anchor, rejecting unpaired, nested or duplicated ones."""
    for match in _ANY_MARKER_RE.finditer(body):
        kind = match.group("kind")
        if kind not in ("block", "point"):
            raise SkillError(f"{origin}: unknown anchor marker `{match.group(0)}`")

    blocks: dict[str, Block] = {}
    points: dict[str, Point] = {}
    open_stack: list[re.Match[str]] = []
    markers = sorted(
        list(BLOCK_OPEN_RE.finditer(body))
        + list(BLOCK_CLOSE_RE.finditer(body))
        + list(POINT_RE.finditer(body)),
        key=lambda m: m.start(),
    )
    for match in markers:
        text = match.group(0)
        if BLOCK_CLOSE_RE.fullmatch(text):
            if not open_stack:
                raise SkillError(f"{origin}: closing block marker with no matching open")
            opener = open_stack.pop()
            block = Block(
                id=opener.group("id"),
                when=opener.group("when"),
                open_start=opener.start(),
                open_end=opener.end(),
                close_start=match.start(),
                close_end=match.end(),
            )
            blocks[block.id] = block
        elif POINT_RE.fullmatch(text):
            point_id = match.group("id")
            if point_id in points:
                raise SkillError(f"{origin}: duplicate point id `{point_id}`")
            points[point_id] = Point(id=point_id, start=match.start(), end=match.end())
        else:
            if open_stack:
                raise SkillError(
                    f"{origin}: block `{match.group('id')}` is nested inside "
                    f"`{open_stack[-1].group('id')}`; nesting is not supported"
                )
            if match.group("id") in blocks:
                raise SkillError(f"{origin}: duplicate block id `{match.group('id')}`")
            open_stack.append(match)
    if open_stack:
        raise SkillError(f"{origin}: block `{open_stack[-1].group('id')}` is never closed")
    overlap = set(blocks) & set(points)
    if overlap:
        raise SkillError(
            f"{origin}: id(s) {', '.join(sorted(overlap))} used as both block and point"
        )
    return Anchors(blocks=blocks, points=points)


def line_span(text: str, start: int, end: int) -> tuple[int, int]:
    """Widen a marker span to whole lines when the marker sits alone on its line."""
    line_start = text.rfind("\n", 0, start) + 1
    newline = text.find("\n", end)
    line_end = len(text) if newline == -1 else newline + 1
    if text[line_start:start].strip() or text[end:line_end].strip():
        return (start, end)
    return (line_start, line_end)


def heal(text: str, index: int) -> str:
    """Collapse a run of blank lines left behind at a cut, and only there."""
    before = index
    while before > 0 and text[before - 1] == "\n":
        before -= 1
    after = index
    while after < len(text) and text[after] == "\n":
        after += 1
    if after - before <= 2:
        return text
    if before == 0:
        return text[after:]
    return text[:before] + "\n\n" + text[after:]


def resolve(body: str, params: dict, origin: str) -> str:
    """Drop blocks whose `when` is false, then strip every remaining marker."""
    anchors = parse_anchors(body, origin)
    cuts: list[tuple[int, int]] = []
    for block in anchors.blocks.values():
        if block.when is not None and not evaluate(block.when, params):
            cuts.append(line_span(body, block.open_start, block.close_end))
        else:
            cuts.append(line_span(body, block.open_start, block.open_end))
            cuts.append(line_span(body, block.close_start, block.close_end))
    for point in anchors.points.values():
        cuts.append(line_span(body, point.start, point.end))

    result = body
    for start, end in sorted(cuts, key=lambda span: span[0], reverse=True):
        result = heal(result[:start] + result[end:], start)
    return result
