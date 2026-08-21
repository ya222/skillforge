"""GitHub Copilot: a managed index plus one `.instructions.md` file per skill."""

from __future__ import annotations

from typing import Any

from skillforge.model import Config
from skillforge.plan import FileWrite, Plan, RegionWrite

DEFAULT_INDEX = ".github/copilot-instructions.md"
DEFAULT_DIR = ".github/instructions"


def apply(skills: list[Any], config: Config, options: dict[str, Any], plan: Plan) -> None:
    del config
    index = options.get("index", DEFAULT_INDEX)
    directory = options.get("path", DEFAULT_DIR).rstrip("/")
    if directory not in plan.managed_dirs:
        plan.managed_dirs.append(directory)

    lines = ["## Agent skills", ""]
    for skill in sorted(skills, key=lambda s: s.name):
        applies_to = ", ".join(skill.globs) if skill.globs else "**"
        lines.append(f"- `{skill.name}` — {skill.description}")
        content = (
            "---\n"
            f"applyTo: '{applies_to}'\n"
            f"description: {skill.description}\n"
            "---\n\n"
            f"{skill.body.lstrip()}"
        )
        plan.files.append(
            FileWrite(f"{directory}/{skill.name}.instructions.md", content.encode("utf-8"))
        )
    plan.regions.append(RegionWrite(path=index, content="\n".join(lines)))
