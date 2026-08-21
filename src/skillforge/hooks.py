"""Local git hooks. This project runs its CI on your machine, never on a runner."""

from __future__ import annotations

from pathlib import Path

from skillforge.errors import SkillforgeError

HOOKS = {
    "pre-commit": "lint check",
    "pre-push": "lint check",
}

TEMPLATE = """#!/bin/sh
# Installed by `skillforge install-hooks`. Delete this file to opt out.
set -e
{command}
"""


def install(root: Path) -> list[Path]:
    git_dir = root / ".git"
    if not git_dir.is_dir():
        raise SkillforgeError(
            f"{root} is not a git repository, so there is nowhere to install hooks"
        )
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    command = "make ci" if (root / "Makefile").is_file() else "skillforge ci"
    written: list[Path] = []
    for name in HOOKS:
        path = hooks_dir / name
        path.write_text(TEMPLATE.format(command=command), encoding="utf-8")
        path.chmod(0o755)
        written.append(path)
    return written
