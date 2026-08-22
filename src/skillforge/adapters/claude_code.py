"""Claude Code reads Agent Skills natively, so this is a straight copy.

Two scopes. The default is the project's `.claude/skills/`, committed with the
repo. `user: true` writes to `~/.claude/skills/` instead, which Claude Code loads
in every project; that directory is shared with hand-written skills, and only the
`sf-` entries in it are ever touched.
"""

from __future__ import annotations

from typing import Any

from skillforge.errors import ConfigError
from skillforge.model import Config
from skillforge.plan import FileWrite, Plan
from skillforge.skills import SKILL_FILE

DEFAULT_PATH = ".claude/skills"
USER_PATH = "~/.claude/skills"


def apply(skills: list[Any], config: Config, options: dict[str, Any], plan: Plan) -> None:
    del config
    if options.get("user") and "path" in options:
        raise ConfigError("target `claude-code`: `user: true` and `path` are mutually exclusive")
    root = (USER_PATH if options.get("user") else options.get("path", DEFAULT_PATH)).rstrip("/")
    if root not in plan.managed_dirs:
        plan.managed_dirs.append(root)
    for skill in skills:
        plan.files.append(FileWrite(f"{root}/{skill.name}/{SKILL_FILE}", skill.skill_md()))
        for relative, content in sorted(skill.files.items()):
            plan.files.append(FileWrite(f"{root}/{skill.name}/{relative}", content))
