"""Cursor project rules: one `.mdc` per skill, loaded on demand by description."""

from __future__ import annotations

from typing import Any

from skillforge.model import Config
from skillforge.plan import FileWrite, Plan

DEFAULT_DIR = ".cursor/rules"


def apply(skills: list[Any], config: Config, options: dict[str, Any], plan: Plan) -> None:
    del config
    directory = options.get("path", DEFAULT_DIR).rstrip("/")
    if directory not in plan.managed_dirs:
        plan.managed_dirs.append(directory)
    for skill in skills:
        globs = ", ".join(skill.globs)
        content = (
            "---\n"
            f"description: {skill.description}\n"
            f"globs: {globs}\n"
            "alwaysApply: false\n"
            "---\n\n"
            f"{skill.body.lstrip()}"
        )
        plan.files.append(FileWrite(f"{directory}/{skill.name}.mdc", content.encode("utf-8")))
