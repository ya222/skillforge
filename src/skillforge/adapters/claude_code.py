"""Claude Code reads Agent Skills natively, so this is a straight copy."""

from __future__ import annotations

from typing import Any

from skillforge.model import Config
from skillforge.plan import FileWrite, Plan
from skillforge.skills import SKILL_FILE

DEFAULT_PATH = ".claude/skills"


def apply(skills: list[Any], config: Config, options: dict[str, Any], plan: Plan) -> None:
    del config
    root = options.get("path", DEFAULT_PATH).rstrip("/")
    if root not in plan.managed_dirs:
        plan.managed_dirs.append(root)
    for skill in skills:
        plan.files.append(FileWrite(f"{root}/{skill.name}/{SKILL_FILE}", skill.skill_md()))
        for relative, content in sorted(skill.files.items()):
            plan.files.append(FileWrite(f"{root}/{skill.name}/{relative}", content))
