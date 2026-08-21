"""A build plan: every byte skillforge intends to write, before it writes any of it.

Planning and writing are separate so that `check` can compare the plan against
what is committed without touching the working tree.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from skillforge.errors import DriftError

REGION_BEGIN = "<!-- skillforge:begin -->"
REGION_END = "<!-- skillforge:end -->"


@dataclass
class FileWrite:
    path: str
    content: bytes

    @property
    def digest(self) -> str:
        return f"sha256:{hashlib.sha256(self.content).hexdigest()}"


@dataclass
class RegionWrite:
    """A managed region inside a file that is otherwise hand-written."""

    path: str
    content: str

    @property
    def key(self) -> str:
        return f"{self.path}#skillforge"

    @property
    def digest(self) -> str:
        return f"sha256:{hashlib.sha256(self.content.encode('utf-8')).hexdigest()}"


@dataclass
class Plan:
    files: list[FileWrite] = field(default_factory=list)
    regions: list[RegionWrite] = field(default_factory=list)
    managed_dirs: list[str] = field(default_factory=list)

    def digests(self) -> dict[str, str]:
        return {
            **{f.path: f.digest for f in self.files},
            **{r.key: r.digest for r in self.regions},
        }


def render_region(existing: str | None, content: str, path: str) -> str:
    """Splice a managed region into a hand-written file, preserving everything else."""
    block = f"{REGION_BEGIN}\n{content.rstrip()}\n{REGION_END}\n"
    if existing is None:
        return block
    start = existing.find(REGION_BEGIN)
    if start == -1:
        separator = (
            "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
        )
        return existing + separator + block
    end = existing.find(REGION_END, start)
    if end == -1:
        raise DriftError(
            f"{path}: `{REGION_BEGIN}` has no matching `{REGION_END}`; "
            "repair the file by hand before rebuilding"
        )
    return existing[:start] + block + existing[end + len(REGION_END) + 1 :]


def extract_region(existing: str, path: str) -> str:
    start = existing.find(REGION_BEGIN)
    if start == -1:
        raise DriftError(f"{path}: managed skillforge region is missing; run `skillforge build`")
    end = existing.find(REGION_END, start)
    if end == -1:
        raise DriftError(f"{path}: `{REGION_BEGIN}` has no matching `{REGION_END}`")
    return existing[start + len(REGION_BEGIN) : end].strip("\n")


def apply(plan: Plan, root: Path) -> list[str]:
    """Write the plan to disk, pruning anything stale under fully managed directories."""
    written: list[str] = []
    planned = {f.path for f in plan.files}

    for directory in plan.managed_dirs:
        target = root / directory
        if not target.is_dir():
            continue
        for existing in sorted(target.rglob("*"), reverse=True):
            relative = existing.relative_to(root).as_posix()
            if existing.is_file() and relative not in planned:
                existing.unlink()
            elif existing.is_dir() and not any(existing.iterdir()):
                existing.rmdir()

    for entry in plan.files:
        path = root / entry.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(entry.content)
        written.append(entry.path)

    for region in plan.regions:
        path = root / region.path
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text(encoding="utf-8") if path.is_file() else None
        path.write_text(render_region(existing, region.content, region.path), encoding="utf-8")
        written.append(region.key)
    return written


def diff(plan: Plan, root: Path) -> list[str]:
    """Everything about the working tree that does not match the plan."""
    problems: list[str] = []
    planned = {f.path for f in plan.files}

    for entry in plan.files:
        path = root / entry.path
        if not path.is_file():
            problems.append(f"missing: {entry.path}")
        elif path.read_bytes() != entry.content:
            problems.append(f"modified: {entry.path}")

    for region in plan.regions:
        path = root / region.path
        if not path.is_file():
            problems.append(f"missing: {region.path}")
            continue
        actual = extract_region(path.read_text(encoding="utf-8"), region.path)
        if actual != region.content.rstrip():
            problems.append(f"modified: {region.key}")

    for directory in plan.managed_dirs:
        target = root / directory
        if not target.is_dir():
            continue
        for existing in target.rglob("*"):
            relative = existing.relative_to(root).as_posix()
            if existing.is_file() and relative not in planned:
                problems.append(f"stale: {relative}")
    return sorted(problems)
