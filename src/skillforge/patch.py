"""Applying consumer patches to a base skill."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path  # noqa: F401
from typing import Any

from skillforge.blocks import heal, line_span, parse_anchors
from skillforge.errors import PatchError
from skillforge.headings import find_section
from skillforge.model import Patch


@dataclass
class PatchResult:
    body: str
    frontmatter: dict[str, Any]
    added_files: dict[str, str] = field(default_factory=dict)
    removed_files: set[str] = field(default_factory=set)


def _resolve_conflicts(patches: list[Patch], origin: str) -> list[Patch]:
    """Two layers touching one target is an error until the later one says force: true."""
    grouped: dict[tuple[str, str], list[Patch]] = {}
    for patch in patches:
        grouped.setdefault(patch.target, []).append(patch)

    keep: list[Patch] = []
    for target, group in grouped.items():
        layers: list[str] = []
        for patch in group:
            if patch.layer not in layers:
                layers.append(patch.layer)
        if len(layers) == 1:
            keep.extend(group)
            continue
        winner = layers[-1]
        winning = [p for p in group if p.layer == winner]
        if not all(p.force for p in winning):
            kind, value = target
            raise PatchError(
                f"{origin}: {kind} `{value}` is patched by layers "
                f"{', '.join(layers)}. The last layer ({winner}) must set `force: true` on "
                "every patch of this target to override the earlier one(s)."
            )
        keep.extend(winning)
    kept = {id(p) for p in keep}
    return [p for p in patches if id(p) in kept]


def _content_of(patch: Patch, origin: str) -> str:
    if patch.source is not None:
        path = patch.root / patch.source
        if not path.is_file():
            raise PatchError(f"{origin}: patch source `{patch.source}` not found at {path}")
        text = path.read_text(encoding="utf-8")
    else:
        text = patch.content or ""
    return text.rstrip("\n") + "\n"


def _set_path(mapping: dict[str, Any], dotted: str, value: Any, origin: str) -> None:
    parts = dotted.split(".")
    cursor = mapping
    for part in parts[:-1]:
        nxt = cursor.get(part)
        if not isinstance(nxt, dict):
            raise PatchError(f"{origin}: frontmatter path `{dotted}` does not exist")
        cursor = nxt
    cursor[parts[-1]] = value


def apply_patches(
    body: str,
    frontmatter: dict[str, Any],
    patches: list[Patch],
    origin: str,
) -> PatchResult:
    """Apply every patch against the *original* body, then splice back to front."""
    patches = _resolve_conflicts(patches, origin)
    result = PatchResult(body=body, frontmatter=frontmatter)
    anchors = parse_anchors(body, origin)
    edits: list[tuple[int, int, str, Patch]] = []

    for patch in patches:
        where = f"{origin}: {patch.describe()}"
        if patch.op == "add-file":
            result.added_files[patch.file] = _content_of(patch, where)
            continue
        if patch.op == "remove-file":
            result.removed_files.add(patch.file)
            continue
        if patch.op == "set-frontmatter":
            _set_path(result.frontmatter, patch.key, patch.content, where)
            continue

        if patch.block:
            block = anchors.blocks.get(patch.block)
            if block is None:
                available = ", ".join(sorted(anchors.blocks)) or "none"
                raise PatchError(
                    f"{where}: block `{patch.block}` is not declared by this skill "
                    f"(available: {available})"
                )
            inner_start, inner_end = block.inner
            if patch.op == "replace":
                edits.append((inner_start, inner_end, "\n" + _content_of(patch, where), patch))
            elif patch.op == "append":
                edits.append((inner_end, inner_end, _content_of(patch, where), patch))
            elif patch.op == "prepend":
                edits.append((inner_start, inner_start, "\n" + _content_of(patch, where), patch))
            elif patch.op == "remove":
                start, end = line_span(body, block.open_start, block.close_end)
                edits.append((start, end, "", patch))
        elif patch.point:
            point = anchors.points.get(patch.point)
            if point is None:
                available = ", ".join(sorted(anchors.points)) or "none"
                raise PatchError(
                    f"{where}: point `{patch.point}` is not declared by this skill "
                    f"(available: {available})"
                )
            start, _ = line_span(body, point.start, point.end)
            edits.append((start, start, _content_of(patch, where) + "\n", patch))
        else:
            section = find_section(body, patch.heading, where)
            actual = section.hash(body)
            if patch.upstream_hash != actual:
                raise PatchError(
                    f"{where}: upstream section `{patch.heading}` has changed.\n"
                    f"  pinned:  {patch.upstream_hash}\n"
                    f"  current: {actual}\n"
                    "Re-read the upstream section, confirm the patch still makes sense, "
                    "then update `upstream_hash`."
                )
            if patch.op == "replace":
                edits.append(
                    (section.body_start, section.end, _content_of(patch, where) + "\n", patch)
                )
            elif patch.op == "append":
                edits.append((section.end, section.end, _content_of(patch, where) + "\n", patch))
            elif patch.op == "prepend":
                edits.append(
                    (
                        section.body_start,
                        section.body_start,
                        _content_of(patch, where) + "\n",
                        patch,
                    )
                )
            elif patch.op == "remove":
                edits.append((section.start, section.end, "", patch))

    _reject_overlaps(edits, origin)
    text = body
    for start, end, replacement, _ in sorted(edits, key=lambda e: e[0], reverse=True):
        text = text[:start] + replacement + text[end:]
        if not replacement:
            text = heal(text, start)
    result.body = text
    return result


def _reject_overlaps(edits: list[tuple[int, int, str, Patch]], origin: str) -> None:
    spans = sorted((e for e in edits if e[0] != e[1]), key=lambda e: e[0])
    for left, right in zip(spans, spans[1:], strict=False):
        if right[0] < left[1]:
            raise PatchError(
                f"{origin}: patches overlap in the document: "
                f"`{left[3].describe()}` and `{right[3].describe()}`"
            )
