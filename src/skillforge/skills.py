"""Reading a base skill directory off disk."""

from __future__ import annotations

import hashlib
from pathlib import Path

from skillforge.errors import SkillError
from skillforge.model import SKILL_NAME_RE, Skill, SkillMeta
from skillforge.skillfile import parse_skillfile

SKILL_FILE = "SKILL.md"


def load_skill(directory: Path, origin: str | None = None) -> Skill:
    origin = origin or str(directory)
    path = directory / SKILL_FILE
    if not path.is_file():
        raise SkillError(f"{origin}: no {SKILL_FILE} in {directory}")
    parsed = parse_skillfile(path.read_text(encoding="utf-8"), origin)
    frontmatter = parsed.frontmatter

    name = frontmatter.get("name")
    if not isinstance(name, str) or not SKILL_NAME_RE.match(name):
        raise SkillError(f"{origin}: `name` must be lower-kebab-case, got {name!r}")
    if name != directory.name:
        raise SkillError(f"{origin}: `name: {name}` does not match directory `{directory.name}`")
    description = frontmatter.get("description")
    if not isinstance(description, str) or not description.strip():
        raise SkillError(f"{origin}: `description` is required and drives when the skill triggers")

    meta_raw = (frontmatter.get("metadata") or {}).get("skillforge")
    meta = SkillMeta.parse(meta_raw, origin)

    files = sorted(
        str(p.relative_to(directory).as_posix())
        for p in directory.rglob("*")
        if p.is_file() and p.name != SKILL_FILE
    )
    return Skill(
        name=name,
        description=description,
        directory=directory,
        frontmatter=frontmatter,
        body=parsed.body,
        meta=meta,
        files=files,
        origin=origin,
    )


def source_hash(skill: Skill) -> str:
    """Hash of the base skill exactly as authored upstream."""
    digest = hashlib.sha256()
    for relative in [SKILL_FILE, *skill.files]:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update((skill.directory / relative).read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"
