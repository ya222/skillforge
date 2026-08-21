"""AGENTS.md index, for every harness that reads AGENTS.md and has no skill loader.

Covers Codex, Gemini CLI and opencode. The index is a managed region, so the rest
of the file stays hand-written.
"""

from __future__ import annotations

from typing import Any

from skillforge.adapters.copilot import one_line
from skillforge.model import Config
from skillforge.plan import Plan, RegionWrite

DEFAULT_PATH = "AGENTS.md"
DEFAULT_HEADING = "## Agent skills"


def apply(skills: list[Any], config: Config, options: dict[str, Any], plan: Plan) -> None:
    path = options.get("path", DEFAULT_PATH)
    heading = options.get("heading", DEFAULT_HEADING)
    lines = [
        heading,
        "",
        "Read the linked file in full before acting on a skill. Load a skill when its "
        "description matches the task at hand.",
        "",
    ]
    for skill in sorted(skills, key=lambda s: s.name):
        target = f"{config.output}/{skill.name}/SKILL.md"
        lines.append(f"- [`{skill.name}`]({target}) — {one_line(skill.description)}")
    plan.regions.append(RegionWrite(path=path, content="\n".join(lines)))
