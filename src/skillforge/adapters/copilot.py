"""GitHub Copilot: a managed index plus one `.instructions.md` file per skill."""

from __future__ import annotations

from typing import Any

import yaml

from skillforge.model import Config
from skillforge.plan import FileWrite, Plan, RegionWrite

DEFAULT_INDEX = ".github/copilot-instructions.md"
DEFAULT_DIR = ".github/instructions"


def one_line(text: str) -> str:
    """A description spanning lines would break the one-bullet-per-skill index."""
    return " ".join(text.split())


def apply(skills: list[Any], config: Config, options: dict[str, Any], plan: Plan) -> None:
    del config
    index = options.get("index", DEFAULT_INDEX)
    directory = options.get("path", DEFAULT_DIR).rstrip("/")
    if directory not in plan.managed_dirs:
        plan.managed_dirs.append(directory)

    lines = ["## Agent skills", ""]
    for skill in sorted(skills, key=lambda s: s.name):
        applies_to = ", ".join(skill.globs) if skill.globs else "**"
        lines.append(f"- `{skill.name}` — {one_line(skill.description)}")
        # Dumped rather than concatenated: a description containing `: ` would
        # otherwise produce a file Copilot cannot parse.
        front = yaml.safe_dump(
            {"applyTo": applies_to, "description": skill.description},
            sort_keys=False,
            allow_unicode=True,
            width=10_000,
        )
        content = f"---\n{front}---\n\n{skill.body.lstrip()}"
        plan.files.append(
            FileWrite(f"{directory}/{skill.name}.instructions.md", content.encode("utf-8"))
        )
    plan.regions.append(RegionWrite(path=index, content="\n".join(lines)))
