"""Reading and writing the SKILL.md envelope (YAML frontmatter + markdown body)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml

from skillforge.errors import SkillError

_DELIMITER = "---"


@dataclass
class Skillfile:
    frontmatter: dict[str, Any]
    body: str


def parse_skillfile(text: str, origin: str) -> Skillfile:
    if not text.startswith(_DELIMITER + "\n"):
        raise SkillError(f"{origin}: must start with a `---` YAML frontmatter delimiter")
    end = text.find("\n" + _DELIMITER, len(_DELIMITER))
    if end == -1:
        raise SkillError(f"{origin}: frontmatter is never closed with `---`")
    raw = text[len(_DELIMITER) + 1 : end + 1]
    rest = text[end + 1 + len(_DELIMITER) :]
    if rest.startswith("\n"):
        rest = rest[1:]
    try:
        frontmatter = yaml.safe_load(raw) or {}
    except yaml.YAMLError as exc:
        raise SkillError(f"{origin}: frontmatter is not valid YAML: {exc}") from exc
    if not isinstance(frontmatter, dict):
        raise SkillError(
            f"{origin}: frontmatter must be a mapping, got {type(frontmatter).__name__}"
        )
    return Skillfile(frontmatter=frontmatter, body=rest)


def dump_skillfile(frontmatter: dict[str, Any], body: str) -> str:
    raw = yaml.safe_dump(
        frontmatter,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=10_000,
    )
    stripped = body.lstrip("\n")
    return f"{_DELIMITER}\n{raw}{_DELIMITER}\n\n{stripped}"
