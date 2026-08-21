"""Static checks on base skills, independent of any consumer configuration."""

from __future__ import annotations

import re
from pathlib import Path

from skillforge import expr
from skillforge.blocks import parse_anchors
from skillforge.errors import SkillError
from skillforge.params import (
    _LOOKS_LIKE_PARAM_RE,
    _PARAM_PATH_RE,
    PLACEHOLDER_RE,
)
from skillforge.skills import SKILL_FILE, load_skill

MAX_NAME = 64
MAX_DESCRIPTION = 1024
SOFT_MAX_LINES = 500

_LINK_RE = re.compile(r"\[[^\]]*\]\((?P<target>[^)\s]+)\)")


def lint_skill(directory: Path) -> list[str]:
    """Return warnings. Anything that makes a skill unusable is raised, not returned."""
    origin = str(directory / SKILL_FILE)
    skill = load_skill(directory, origin)
    warnings: list[str] = []

    if not skill.meta.declared:
        raise SkillError(
            f"{origin}: missing `metadata.skillforge`; a skill this library publishes declares "
            "at least a version"
        )
    if len(skill.name) > MAX_NAME:
        raise SkillError(f"{origin}: name is {len(skill.name)} chars, the limit is {MAX_NAME}")
    if len(skill.description) > MAX_DESCRIPTION:
        raise SkillError(
            f"{origin}: description is {len(skill.description)} chars, "
            f"the limit is {MAX_DESCRIPTION}"
        )
    if "use when" not in skill.description.lower():
        warnings.append(
            f"{origin}: description does not say when to use the skill; "
            "a description without trigger conditions rarely fires"
        )

    declared = set(skill.meta.params)
    anchors = parse_anchors(skill.body, origin)
    for block in anchors.blocks.values():
        if block.when is None:
            continue
        for name in expr.references(block.when):
            if name not in declared:
                raise SkillError(
                    f"{origin}: block `{block.id}` tests `params.{name}`, which is not declared"
                )

    for text, label in [(skill.body, "body"), (skill.description, "description")]:
        for match in PLACEHOLDER_RE.finditer(text):
            inner = match.group("inner")
            path = _PARAM_PATH_RE.match(inner)
            if path is None:
                if _LOOKS_LIKE_PARAM_RE.match(inner):
                    raise SkillError(
                        f"{origin}: {label} contains `{{{{ {inner} }}}}`, which looks like a param "
                        "reference but is not one"
                    )
                continue
            if path.group(1) not in declared:
                raise SkillError(
                    f"{origin}: {label} uses `params.{path.group(1)}`, which is not declared"
                )

    used = {
        m.group(1)
        for text in (skill.body, skill.description)
        for m in (_PARAM_PATH_RE.match(p.group("inner")) for p in PLACEHOLDER_RE.finditer(text))
        if m
    }
    for block in anchors.blocks.values():
        if block.when:
            used |= expr.references(block.when)
    for unused in sorted(declared - used):
        warnings.append(f"{origin}: param `{unused}` is declared but never used")

    for match in _LINK_RE.finditer(skill.body):
        target = match.group("target")
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        # A link may carry a fragment or query; only the path part is a file.
        target = target.split("#", 1)[0].split("?", 1)[0]
        if not target:
            continue
        if not (directory / target).exists():
            raise SkillError(f"{origin}: link target `{target}` does not exist in the skill")

    lines = skill.body.count("\n") + 1
    if lines > SOFT_MAX_LINES:
        warnings.append(
            f"{origin}: body is {lines} lines; over ~{SOFT_MAX_LINES} the agent is better served "
            "by moving detail into a reference file"
        )
    return warnings


def lint_tree(skills_dir: Path) -> list[str]:
    if not skills_dir.is_dir():
        raise SkillError(f"no skills directory at {skills_dir}")
    warnings: list[str] = []
    for directory in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        warnings.extend(lint_skill(directory))
    return warnings
