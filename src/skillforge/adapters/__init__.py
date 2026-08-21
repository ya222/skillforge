"""Harness adapters.

The rendered skill directory under `output:` is the canonical artifact. Adapters
translate it into whatever shape a specific harness expects, and nothing else in
skillforge knows those shapes exist.

An adapter takes the rendered skills, the merged config, its own options, and the
plan it should append writes to. It must never touch the filesystem itself.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from skillforge.adapters import agents_md, claude_code, copilot, cursor
from skillforge.model import Config
from skillforge.plan import Plan

Adapter = Callable[[list[Any], Config, dict[str, Any], Plan], None]

ADAPTERS: dict[str, Adapter] = {
    "claude-code": claude_code.apply,
    "agents-md": agents_md.apply,
    "copilot": copilot.apply,
    "cursor": cursor.apply,
}
