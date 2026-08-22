"""Typed representations of everything skillforge reads off disk."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from skillforge.errors import ConfigError, SkillError

MISSING = object()

SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Every rendered skill is named `sf-<name>`, and skillforge only ever creates,
# rewrites or prunes entries carrying this prefix. A managed directory can
# therefore be shared with hand-written skills, including a user's ~/.claude/skills.
RENDERED_PREFIX = "sf-"
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

PARAM_TYPES = ("string", "bool", "int", "list", "enum")
PATCH_OPS = (
    "replace",
    "append",
    "prepend",
    "insert",
    "remove",
    "add-file",
    "remove-file",
    "set-frontmatter",
)


def _reject_unknown(mapping: dict[str, Any], allowed: tuple[str, ...], origin: str) -> None:
    unknown = sorted(set(mapping) - set(allowed))
    if unknown:
        raise ConfigError(
            f"{origin}: unknown key(s) {', '.join(unknown)}; allowed: {', '.join(sorted(allowed))}"
        )


@dataclass
class ParamSpec:
    name: str
    type: str
    description: str = ""
    default: Any = MISSING
    values: list[Any] | None = None
    items: list[Any] | None = None

    @property
    def required(self) -> bool:
        return self.default is MISSING

    @classmethod
    def parse(cls, name: str, raw: Any, origin: str) -> ParamSpec:
        where = f"{origin}: param `{name}`"
        if not isinstance(raw, dict):
            raise SkillError(f"{where}: must be a mapping, got {type(raw).__name__}")
        _reject_unknown(raw, ("type", "description", "default", "values", "items"), where)
        param_type = raw.get("type")
        if param_type not in PARAM_TYPES:
            raise SkillError(
                f"{where}: type must be one of {', '.join(PARAM_TYPES)}, got {param_type!r}"
            )
        values = raw.get("values")
        if param_type == "enum" and not values:
            raise SkillError(f"{where}: type `enum` needs a non-empty `values` list")
        if param_type != "enum" and values is not None:
            raise SkillError(f"{where}: `values` is only meaningful for type `enum`")
        items = raw.get("items")
        if items is not None and param_type != "list":
            raise SkillError(f"{where}: `items` is only meaningful for type `list`")
        return cls(
            name=name,
            type=param_type,
            description=raw.get("description", ""),
            default=raw.get("default", MISSING),
            values=values,
            items=items,
        )


@dataclass
class SkillMeta:
    version: str
    globs: list[str] = field(default_factory=list)
    attribution: str | None = None
    params: dict[str, ParamSpec] = field(default_factory=dict)
    declared: bool = True

    @classmethod
    def parse(cls, raw: Any, origin: str) -> SkillMeta:
        """Parse `metadata.skillforge`, which a plain Agent Skill will not have.

        Importing a skill from a library that never heard of skillforge has to
        work, so an absent block yields an unversioned, param-less skill. The
        linter is what insists on a declaration, and it only runs on skills this
        repository authors.
        """
        if raw is None:
            return cls(version="0.0.0", declared=False)
        if not isinstance(raw, dict):
            raise SkillError(f"{origin}: `metadata.skillforge` must be a mapping")
        _reject_unknown(raw, ("version", "globs", "attribution", "params"), origin)
        version = raw.get("version")
        if not isinstance(version, str) or not SEMVER_RE.match(version):
            raise SkillError(
                f"{origin}: `metadata.skillforge.version` must be "
                f"MAJOR.MINOR.PATCH, got {version!r}"
            )
        params_raw = raw.get("params") or {}
        if not isinstance(params_raw, dict):
            raise SkillError(f"{origin}: `metadata.skillforge.params` must be a mapping")
        return cls(
            version=version,
            globs=list(raw.get("globs") or []),
            attribution=raw.get("attribution"),
            params={name: ParamSpec.parse(name, spec, origin) for name, spec in params_raw.items()},
        )


@dataclass
class Skill:
    """A base skill as authored, before params, blocks or patches are resolved."""

    name: str
    description: str
    directory: Path
    frontmatter: dict[str, Any]
    body: str
    meta: SkillMeta
    files: list[str] = field(default_factory=list)
    origin: str = ""


@dataclass
class Source:
    alias: str
    git: str
    ref: str
    path: str = "skills"

    @classmethod
    def parse(cls, alias: str, raw: Any, origin: str) -> Source:
        where = f"{origin}: source `{alias}`"
        if not isinstance(raw, dict):
            raise ConfigError(f"{where}: must be a mapping")
        _reject_unknown(raw, ("git", "ref", "path"), where)
        if not raw.get("git"):
            raise ConfigError(f"{where}: missing `git`")
        if not raw.get("ref"):
            raise ConfigError(f"{where}: missing `ref`")
        return cls(alias=alias, git=raw["git"], ref=raw["ref"], path=raw.get("path", "skills"))


@dataclass
class Patch:
    op: str
    block: str | None = None
    point: str | None = None
    heading: str | None = None
    key: str | None = None
    content: str | None = None
    source: str | None = None
    file: str | None = None
    upstream_hash: str | None = None
    force: bool = False
    layer: str = ""
    root: Path = Path(".")

    @property
    def target(self) -> tuple[str, str]:
        for kind in ("block", "point", "heading", "key", "file"):
            value = getattr(self, kind)
            if value:
                return (kind, value)
        raise ConfigError("patch has no target")

    def describe(self) -> str:
        kind, value = self.target
        return f"{self.op} {kind} `{value}` (layer {self.layer})"

    @classmethod
    def parse(cls, raw: Any, origin: str, layer: str, root: Path) -> Patch:
        if not isinstance(raw, dict):
            raise ConfigError(f"{origin}: each patch must be a mapping")
        _reject_unknown(
            raw,
            (
                "op",
                "block",
                "point",
                "heading",
                "key",
                "content",
                "source",
                "file",
                "upstream_hash",
                "force",
            ),
            origin,
        )
        op = raw.get("op")
        if op not in PATCH_OPS:
            raise ConfigError(f"{origin}: op must be one of {', '.join(PATCH_OPS)}, got {op!r}")
        patch = cls(
            op=op,
            block=raw.get("block"),
            point=raw.get("point"),
            heading=raw.get("heading"),
            key=raw.get("key"),
            content=raw.get("content"),
            source=raw.get("source"),
            file=raw.get("file"),
            upstream_hash=raw.get("upstream_hash"),
            force=bool(raw.get("force", False)),
            layer=layer,
            root=root,
        )
        patch.validate(origin)
        return patch

    def validate(self, origin: str) -> None:
        targets = [t for t in (self.block, self.point, self.heading, self.key) if t]
        if self.op in ("add-file", "remove-file"):
            if not self.file:
                raise ConfigError(f"{origin}: `{self.op}` requires `file`")
            if targets:
                raise ConfigError(f"{origin}: `{self.op}` takes only `file`")
            if self.op == "add-file" and self.content is None and self.source is None:
                raise ConfigError(f"{origin}: `add-file` requires `content` or `source`")
            if self.op == "remove-file" and (self.content is not None or self.source is not None):
                raise ConfigError(f"{origin}: `remove-file` takes no content")
            return
        if self.op == "set-frontmatter":
            if not self.key:
                raise ConfigError(f"{origin}: `set-frontmatter` requires `key`")
            if self.content is None:
                raise ConfigError(f"{origin}: `set-frontmatter` requires `content`")
            return
        if len(targets) != 1:
            raise ConfigError(
                f"{origin}: `{self.op}` needs exactly one of "
                f"block/point/heading, got {len(targets)}"
            )
        if self.point and self.op != "insert":
            raise ConfigError(
                f"{origin}: a `point` target only supports op `insert`, got {self.op}"
            )
        if self.block and self.op == "insert":
            raise ConfigError(f"{origin}: op `insert` targets a `point`, not a `block`")
        if self.heading and self.op == "insert":
            raise ConfigError(f"{origin}: op `insert` targets a `point`, not a `heading`")
        if self.heading and not self.upstream_hash:
            raise ConfigError(
                f"{origin}: heading target `{self.heading}` must pin `upstream_hash`; "
                "heading paths are unstable across upstream versions"
            )
        if self.file:
            raise ConfigError(
                f"{origin}: `file` names a destination and only applies to add-file/remove-file; "
                "use `source` to read patch content from a path"
            )
        if self.op != "remove" and self.content is None and self.source is None:
            raise ConfigError(f"{origin}: `{self.op}` requires `content` or `source`")
        if self.op == "remove" and (self.content is not None or self.source is not None):
            raise ConfigError(f"{origin}: `remove` takes no `content` or `source`")


@dataclass
class SkillRequest:
    """One entry in the `skills:` list of a skillforge.yaml."""

    ref: str
    name: str
    params: dict[str, Any] = field(default_factory=dict)
    patches: list[Patch] = field(default_factory=list)
    layer: str = ""
    root: Path = Path(".")

    @property
    def is_local(self) -> bool:
        return self.ref.startswith(".") or self.ref.startswith("/")

    @property
    def source_alias(self) -> str | None:
        return None if self.is_local else self.ref.split("/", 1)[0]

    @property
    def skill_path(self) -> str:
        return self.ref if self.is_local else self.ref.split("/", 1)[1]

    @property
    def identity(self) -> str:
        """What this entry actually points at, so two layers can be compared.

        Local refs are relative to the layer that declared them, so `./skills/x`
        in one layer and `../skills/x` in another can be the same skill.
        """
        if self.is_local:
            return str((self.root / self.skill_path).resolve())
        return self.ref

    @classmethod
    def parse(cls, raw: Any, origin: str, layer: str, root: Path) -> SkillRequest:
        if not isinstance(raw, dict):
            raise ConfigError(f"{origin}: each `skills` entry must be a mapping")
        _reject_unknown(raw, ("from", "as", "params", "patches"), origin)
        ref = raw.get("from")
        if not ref:
            raise ConfigError(f"{origin}: each `skills` entry needs `from`")
        if not (ref.startswith(".") or ref.startswith("/")) and "/" not in ref:
            raise ConfigError(
                f"{origin}: `from: {ref}` must be `<source-alias>/<skill>` or a local path"
            )
        name = raw.get("as") or Path(ref).name
        if not SKILL_NAME_RE.match(name):
            raise ConfigError(f"{origin}: skill name `{name}` must be lower-kebab-case")
        where = f"{origin}: skill `{name}`"
        return cls(
            ref=ref,
            name=name,
            params=dict(raw.get("params") or {}),
            patches=[
                Patch.parse(p, f"{where} patch #{i + 1}", layer, root)
                for i, p in enumerate(raw.get("patches") or [])
            ],
            layer=layer,
            root=root,
        )


@dataclass
class Config:
    root: Path
    version: int = 1
    extends: list[str] = field(default_factory=list)
    sources: dict[str, Source] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    skills: list[SkillRequest] = field(default_factory=list)
    targets: dict[str, dict[str, Any]] = field(default_factory=dict)
    output: str = ".agents/skills"
    present: set[str] = field(default_factory=set)
