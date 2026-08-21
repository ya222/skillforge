"""Fetching upstream skill libraries into a local, gitignored cache."""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from skillforge.errors import SourceError
from skillforge.model import Source

CACHE_DIR = Path(".skillforge") / "cache"


@dataclass
class ResolvedSource:
    alias: str
    git: str
    ref: str
    commit: str
    path: Path


def _git(args: list[str], cwd: Path | None = None) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        location = f" in {cwd}" if cwd else ""
        raise SourceError(
            f"`git {' '.join(args)}`{location} failed with exit {process.returncode}:\n"
            f"{process.stderr.strip()}"
        )
    return process.stdout.strip()


def _slug(source: Source) -> str:
    digest = hashlib.sha1(f"{source.git}#{source.ref}".encode()).hexdigest()[:10]
    name = re.sub(r"[^A-Za-z0-9]+", "-", source.git.rstrip("/").split("/")[-1]).strip("-")
    return f"{name}-{digest}"


def _has_commit(repo: Path, commit: str) -> bool:
    return (
        subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=repo,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def fetch(source: Source, root: Path, locked_commit: str | None = None) -> ResolvedSource:
    """Materialise a source at a specific commit.

    When the lockfile pins a commit that the cache already holds, no network
    access happens at all. Otherwise the ref is fetched and resolved.
    """
    cache = root / CACHE_DIR / _slug(source)
    if not (cache / ".git").is_dir():
        cache.parent.mkdir(parents=True, exist_ok=True)
        _git(["clone", "--quiet", "--filter=blob:none", source.git, str(cache)])

    if locked_commit and _has_commit(cache, locked_commit):
        commit = locked_commit
    else:
        _git(["fetch", "--quiet", "--tags", "--force", "origin"], cwd=cache)
        commit = _resolve_ref(cache, source)

    _git(["checkout", "--quiet", "--detach", commit], cwd=cache)
    return ResolvedSource(
        alias=source.alias, git=source.git, ref=source.ref, commit=commit, path=cache
    )


def _resolve_ref(repo: Path, source: Source) -> str:
    for candidate in (f"refs/tags/{source.ref}", f"origin/{source.ref}", source.ref):
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"{candidate}^{{commit}}"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    raise SourceError(f"source `{source.alias}`: ref `{source.ref}` does not exist in {source.git}")
