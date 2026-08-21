"""Cursor project rules: one `.mdc` per skill, loaded on demand by description."""

from __future__ import annotations

from typing import Any

import yaml

from skillforge.model import Config
from skillforge.plan import FileWrite, Plan

DEFAULT_DIR = ".cursor/rules"


def apply(skills: list[Any], config: Config, options: dict[str, Any], plan: Plan) -> None:
    del config
    directory = options.get("path", DEFAULT_DIR).rstrip("/")
    if directory not in plan.managed_dirs:
        plan.managed_dirs.append(directory)
    for skill in skills:
        # Dumped rather than concatenated: a description containing `: ` would
        # otherwise produce a file Cursor cannot parse.
        front = yaml.safe_dump(
            {
                "description": skill.description,
                "globs": ", ".join(skill.globs),
                "alwaysApply": False,
            },
            sort_keys=False,
            allow_unicode=True,
            width=10_000,
        )
        content = f"---\n{front}---\n\n{skill.body.lstrip()}"
        plan.files.append(FileWrite(f"{directory}/{skill.name}.mdc", content.encode("utf-8")))
