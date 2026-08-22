"""Resolving declared params against shared values and per-skill overrides."""

from __future__ import annotations

import re
from typing import Any

from skillforge.errors import ParamError
from skillforge.model import MISSING, ParamSpec

# `{{ params.name }}`. A backslash escape (`\{{`) renders a literal `{{`.
PLACEHOLDER_RE = re.compile(r"(?<!\\)\{\{\s*(?P<inner>[^{}]*?)\s*\}\}")
_PARAM_PATH_RE = re.compile(r"^params\.([A-Za-z_][A-Za-z0-9_]*)$")
# Skill bodies legitimately contain other `{{ ... }}` (template examples, mustache
# snippets). Only placeholders that claim to be param references are validated.
_LOOKS_LIKE_PARAM_RE = re.compile(r"^params?\b")


def resolve(
    specs: dict[str, ParamSpec],
    globals_: dict[str, Any],
    overrides: dict[str, Any],
    origin: str,
) -> dict[str, Any]:
    """Layer defaults < shared_params < per-skill params, then type-check.

    Shared params that a skill does not declare are ignored: they exist for
    whichever skills do declare them. Per-skill overrides are strict, because an
    override naming an undeclared param is always a typo.
    """
    unknown = sorted(set(overrides) - set(specs))
    if unknown:
        declared = ", ".join(sorted(specs)) or "none"
        raise ParamError(
            f"{origin}: param override(s) {', '.join(unknown)} not declared by this skill "
            f"(declared: {declared})"
        )

    resolved: dict[str, Any] = {}
    for name, spec in specs.items():
        if name in overrides:
            value = overrides[name]
        elif name in globals_:
            value = globals_[name]
        elif spec.default is not MISSING:
            value = spec.default
        else:
            raise ParamError(
                f"{origin}: param `{name}` is required and has no value "
                f"({spec.description or 'no description'})"
            )
        resolved[name] = _check(spec, value, origin)
    return resolved


def _check(spec: ParamSpec, value: Any, origin: str) -> Any:
    where = f"{origin}: param `{spec.name}`"
    if spec.type == "string":
        if not isinstance(value, str):
            raise ParamError(f"{where}: expected string, got {type(value).__name__}")
    elif spec.type == "bool":
        if not isinstance(value, bool):
            raise ParamError(f"{where}: expected bool, got {type(value).__name__}")
    elif spec.type == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ParamError(f"{where}: expected int, got {type(value).__name__}")
    elif spec.type == "enum":
        if value not in (spec.values or []):
            raise ParamError(
                f"{where}: {value!r} is not one of {', '.join(map(str, spec.values or []))}"
            )
    elif spec.type == "list":
        if not isinstance(value, list):
            raise ParamError(f"{where}: expected list, got {type(value).__name__}")
        if spec.items is not None:
            bad = [v for v in value if v not in spec.items]
            if bad:
                raise ParamError(
                    f"{where}: {', '.join(map(str, bad))} not in allowed items "
                    f"{', '.join(map(str, spec.items))}"
                )
    return value


def render_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def substitute(text: str, params: dict[str, Any], origin: str) -> str:
    """Replace every `{{ params.x }}` placeholder. Unknown or malformed ones are errors."""

    def replace(match: re.Match[str]) -> str:
        inner = match.group("inner")
        path = _PARAM_PATH_RE.match(inner)
        if path is None:
            if _LOOKS_LIKE_PARAM_RE.match(inner):
                raise ParamError(
                    f"{origin}: `{{{{ {inner} }}}}` looks like a param reference but is not one; "
                    "the only supported form is `{{ params.<name> }}`"
                )
            return match.group(0)
        name = path.group(1)
        if name not in params:
            declared = ", ".join(sorted(params)) or "none"
            raise ParamError(
                f"{origin}: `{{{{ params.{name} }}}}` is not declared by this skill "
                f"(declared: {declared})"
            )
        return render_value(params[name])

    return PLACEHOLDER_RE.sub(replace, text).replace("\\{{", "{{")
