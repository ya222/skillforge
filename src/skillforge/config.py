"""Loading and layering skillforge.yaml files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from skillforge.errors import ConfigError
from skillforge.model import Config, SkillRequest, Source, _reject_unknown

CONFIG_NAME = "skillforge.yaml"
TOP_LEVEL_KEYS = ("version", "extends", "sources", "skills", "shared_params", "targets", "output")


def load_raw(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"no {CONFIG_NAME} at {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: must be a mapping")
    _reject_unknown(data, TOP_LEVEL_KEYS, str(path))
    version = data.get("version", 1)
    if version != 1:
        raise ConfigError(f"{path}: unsupported config version {version!r}, this build speaks 1")
    return data


def parse_layer(path: Path, layer: str) -> Config:
    """Parse one skillforge.yaml without following `extends`."""
    raw = load_raw(path)
    root = path.parent
    origin = f"{path}"
    sources = {
        alias: Source.parse(alias, spec, origin)
        for alias, spec in (raw.get("sources") or {}).items()
    }
    skills = [
        SkillRequest.parse(entry, f"{origin} skills[{index}]", layer, root)
        for index, entry in enumerate(raw.get("skills") or [])
    ]
    names = [s.name for s in skills]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        raise ConfigError(
            f"{origin}: skill name(s) {', '.join(duplicates)} defined twice in one layer; "
            "disambiguate with `as:`"
        )
    return Config(
        root=root,
        extends=list(raw.get("extends") or []),
        sources=sources,
        params=dict(raw.get("shared_params") or {}),
        skills=skills,
        targets=dict(raw.get("targets") or {}),
        output=raw.get("output", ".agents/skills"),
        present=set(raw),
    )


def merge(base: Config, overlay: Config) -> Config:
    """Layer `overlay` on top of `base`. Later layers win on scalars, patches accumulate."""
    for alias, source in overlay.sources.items():
        existing = base.sources.get(alias)
        if existing and (existing.git, existing.ref, existing.path) != (
            source.git,
            source.ref,
            source.path,
        ):
            raise ConfigError(
                f"source alias `{alias}` means {existing.git}@{existing.ref} in one layer and "
                f"{source.git}@{source.ref} in another; rename one of them"
            )
        base.sources[alias] = source

    base.params.update(overlay.params)

    by_name = {skill.name: skill for skill in base.skills}
    for skill in overlay.skills:
        existing = by_name.get(skill.name)
        if existing is None:
            base.skills.append(skill)
            by_name[skill.name] = skill
            continue
        if existing.identity != skill.identity:
            raise ConfigError(
                f"skill `{skill.name}` comes from `{existing.ref}` in one layer and "
                f"`{skill.ref}` in another; disambiguate with `as:`"
            )
        existing.params.update(skill.params)
        existing.patches.extend(skill.patches)

    if "targets" in overlay.present:
        base.targets = overlay.targets
    if "output" in overlay.present:
        base.output = overlay.output
    # A merged layer carries forward which keys its own parents set, so a value
    # declared once at the top of an `extends` chain survives every layer below
    # that stays silent about it.
    base.present |= overlay.present
    return base
