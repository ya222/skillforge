"""Test helpers. Tests build real repositories on disk and run the real pipeline."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")
    return path


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return tmp_path


def make_skill(
    root: Path,
    name: str = "demo",
    *,
    description: str = "A demo skill. Use when demonstrating skillforge.",
    params: dict | None = None,
    body: str = "Body.\n",
    version: str = "1.0.0",
    globs: list[str] | None = None,
) -> Path:
    frontmatter = {
        "name": name,
        "description": description,
        "metadata": {
            "skillforge": {
                "version": version,
                **({"globs": globs} if globs else {}),
                **({"params": params} if params else {}),
            }
        },
    }
    directory = root / "skills" / name
    directory.mkdir(parents=True, exist_ok=True)
    dumped = yaml.safe_dump(frontmatter, sort_keys=False)
    (directory / "SKILL.md").write_text(f"---\n{dumped}---\n\n{body}", encoding="utf-8")
    return directory


def make_config(root: Path, **config) -> Path:
    config.setdefault("version", 1)
    config.setdefault("targets", {"claude-code": {}})
    path = root / "skillforge.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return path


def rendered(root: Path, name: str, output: str = ".agents/skills") -> str:
    return (root / output / name / "SKILL.md").read_text(encoding="utf-8")
