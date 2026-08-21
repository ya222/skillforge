"""The build pipeline: config + sources -> rendered skills -> a write plan."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path

from skillforge import blocks
from skillforge import config as config_module
from skillforge import lock as lock_module
from skillforge import sources as sources_module
from skillforge.adapters import ADAPTERS
from skillforge.errors import ConfigError, SkillError
from skillforge.model import Config, SkillMeta, SkillRequest
from skillforge.params import resolve as resolve_params
from skillforge.params import substitute
from skillforge.patch import apply_patches
from skillforge.plan import FileWrite, Plan
from skillforge.skillfile import dump_skillfile
from skillforge.skills import SKILL_FILE, load_skill, source_hash
from skillforge.sources import ResolvedSource

TEXT_SUFFIXES = (".md", ".txt")


@dataclass
class RenderedSkill:
    name: str
    description: str
    frontmatter: dict
    body: str
    files: dict[str, bytes] = field(default_factory=dict)
    globs: list[str] = field(default_factory=list)
    ref: str = ""
    version: str = ""
    source_hash: str = ""

    def skill_md(self) -> bytes:
        return dump_skillfile(self.frontmatter, self.body).encode("utf-8")


@dataclass
class Build:
    config: Config
    skills: list[RenderedSkill]
    sources: dict[str, ResolvedSource]
    plan: Plan
    lock: lock_module.Lock


def load_layered_config(
    root: Path, lock: lock_module.Lock, refresh: set[str] | None = None
) -> tuple[Config, dict[str, ResolvedSource]]:
    """Resolve `extends` depth-first, fetching any source a layer is pulled from."""
    refresh = refresh or set()
    resolved: dict[str, ResolvedSource] = {}
    visited: set[Path] = set()

    def pinned(alias: str) -> str | None:
        return None if alias in refresh else lock.commit_for(alias)

    def load(path: Path, layer: str) -> Config:
        real = path.resolve()
        if real in visited:
            raise ConfigError(f"{path}: circular `extends` chain")
        visited.add(real)
        current = config_module.parse_layer(path, layer)
        merged = Config(root=current.root)
        for entry in current.extends:
            parent_path = _extends_path(entry, current, root, pinned, resolved, path)
            config_module.merge(merged, load(parent_path, entry))
        config_module.merge(merged, current)
        merged.root = current.root
        merged.present = current.present | merged.present
        return merged

    top = load(root / config_module.CONFIG_NAME, "root")
    for alias, source in top.sources.items():
        if alias not in resolved:
            resolved[alias] = sources_module.fetch(source, root, pinned(alias))
    return top, resolved


def _extends_path(
    entry: str,
    current: Config,
    root: Path,
    pinned,
    resolved: dict[str, ResolvedSource],
    origin: Path,
) -> Path:
    if entry in current.sources:
        if entry not in resolved:
            resolved[entry] = sources_module.fetch(current.sources[entry], root, pinned(entry))
        return resolved[entry].path / config_module.CONFIG_NAME
    candidate = (current.root / entry).resolve()
    if candidate.is_dir():
        candidate = candidate / config_module.CONFIG_NAME
    if not candidate.is_file():
        raise ConfigError(
            f"{origin}: `extends: {entry}` is neither a declared source alias nor a path to a "
            f"{config_module.CONFIG_NAME}"
        )
    return candidate


def base_directory(
    request: SkillRequest, config: Config, resolved: dict[str, ResolvedSource]
) -> Path:
    if request.is_local:
        return (request.root / request.skill_path).resolve()
    alias = request.source_alias
    source = config.sources.get(alias)
    if source is None:
        known = ", ".join(sorted(config.sources)) or "none"
        raise ConfigError(
            f"skill `{request.name}`: unknown source alias `{alias}` (declared: {known})"
        )
    return resolved[alias].path / source.path / request.skill_path


def render_skill(
    request: SkillRequest, config: Config, resolved: dict[str, ResolvedSource]
) -> RenderedSkill:
    directory = base_directory(request, config, resolved)
    origin = f"skill `{request.name}` ({request.ref})"
    base = load_skill(directory, origin)

    patched = apply_patches(base.body, copy.deepcopy(base.frontmatter), request.patches, origin)
    meta = SkillMeta.parse((patched.frontmatter.get("metadata") or {}).get("skillforge"), origin)
    params = resolve_params(meta.params, config.params, request.params, origin)

    body = blocks.resolve(patched.body, params, origin)
    body = substitute(body, params, origin)
    description = substitute(str(patched.frontmatter["description"]), params, origin)

    files: dict[str, bytes] = {}
    for relative in base.files:
        if relative in patched.removed_files:
            continue
        raw = (directory / relative).read_bytes()
        if relative.endswith(TEXT_SUFFIXES):
            raw = substitute(raw.decode("utf-8"), params, f"{origin} file `{relative}`").encode()
        files[relative] = raw
    for relative in patched.removed_files:
        if relative not in base.files:
            raise SkillError(
                f"{origin}: `remove-file: {relative}` does not exist in the base skill"
            )
    for relative, content in patched.added_files.items():
        files[relative] = substitute(content, params, f"{origin} file `{relative}`").encode()

    frontmatter = {"name": request.name, "description": description}
    for key, value in patched.frontmatter.items():
        if key not in ("name", "description", "metadata"):
            frontmatter[key] = value
    provenance = {"version": meta.version, "source": request.ref}
    if meta.attribution:
        provenance["attribution"] = meta.attribution
    frontmatter["metadata"] = {"skillforge": provenance}

    return RenderedSkill(
        name=request.name,
        description=description,
        frontmatter=frontmatter,
        body=body,
        files=files,
        globs=meta.globs,
        ref=request.ref,
        version=meta.version,
        source_hash=source_hash(base),
    )


def build(root: Path, refresh: set[str] | None = None) -> Build:
    lock = lock_module.load(root)
    config, resolved = load_layered_config(root, lock, refresh)
    if not config.skills:
        raise ConfigError(f"{root / config_module.CONFIG_NAME}: no skills listed")

    skills = [render_skill(request, config, resolved) for request in config.skills]
    plan = Plan(managed_dirs=[config.output])

    for skill in skills:
        prefix = f"{config.output}/{skill.name}"
        plan.files.append(FileWrite(f"{prefix}/{SKILL_FILE}", skill.skill_md()))
        for relative, content in sorted(skill.files.items()):
            plan.files.append(FileWrite(f"{prefix}/{relative}", content))

    for name, options in config.targets.items():
        adapter = ADAPTERS.get(name)
        if adapter is None:
            known = ", ".join(sorted(ADAPTERS))
            raise ConfigError(f"unknown target `{name}` (available: {known})")
        adapter(skills, config, options or {}, plan)

    new_lock = lock_module.Lock(
        sources={
            alias: {"git": source.git, "ref": source.ref, "commit": source.commit}
            for alias, source in sorted(resolved.items())
        },
        skills={
            skill.name: {
                "from": skill.ref,
                "version": skill.version,
                "source_hash": skill.source_hash,
            }
            for skill in skills
        },
        outputs=plan.digests(),
    )
    return Build(config=config, skills=skills, sources=resolved, plan=plan, lock=new_lock)
