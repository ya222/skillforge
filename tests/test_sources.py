"""Importing from a real git repository, pinned by a real commit."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from skillforge import lock as lock_module
from skillforge.errors import SourceError
from skillforge.model import Source
from skillforge.render import build
from skillforge.sources import fetch
from tests.conftest import make_config, make_skill, rendered
from tests.test_render import build_and_write


def git(args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def make_upstream(path: Path, body: str = "## Upstream\n\nOriginal.\n") -> str:
    path.mkdir(parents=True, exist_ok=True)
    git(["init", "-q", "-b", "main"], path)
    git(["config", "user.email", "test@example.com"], path)
    git(["config", "user.name", "Test"], path)
    make_skill(path, name="imported", body=body)
    git(["add", "-A"], path)
    git(["commit", "-qm", "initial"], path)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True, check=True
    ).stdout.strip()


def test_a_skill_is_imported_from_a_git_source(tmp_path):
    upstream = tmp_path / "upstream"
    commit = make_upstream(upstream)
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    make_config(
        consumer,
        sources={"up": {"git": str(upstream), "ref": "main"}},
        skills=[{"from": "up/imported"}],
    )
    result = build_and_write(consumer)
    assert "Original." in rendered(consumer, "imported")
    assert result.lock.sources["up"]["commit"] == commit


def test_the_lock_pins_the_commit_and_a_moved_ref_is_ignored_until_update(tmp_path):
    upstream = tmp_path / "upstream"
    make_upstream(upstream)
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    make_config(
        consumer,
        sources={"up": {"git": str(upstream), "ref": "main"}},
        skills=[{"from": "up/imported"}],
    )
    first = build_and_write(consumer)
    lock_module.dump(first.lock, consumer)

    make_skill(upstream, name="imported", body="## Upstream\n\nMoved on.\n")
    git(["commit", "-aqm", "second"], upstream)

    pinned = build_and_write(consumer)
    assert "Original." in rendered(consumer, "imported")
    assert pinned.lock.sources["up"]["commit"] == first.lock.sources["up"]["commit"]

    refreshed = build(consumer, refresh={"up"})
    assert refreshed.lock.sources["up"]["commit"] != first.lock.sources["up"]["commit"]


def test_an_unknown_ref_fails_loudly(tmp_path):
    upstream = tmp_path / "upstream"
    make_upstream(upstream)
    source = Source(alias="up", git=str(upstream), ref="does-not-exist")
    with pytest.raises(SourceError, match="does not exist"):
        fetch(source, tmp_path / "consumer")


def test_extends_a_config_in_a_git_source(tmp_path):
    upstream = tmp_path / "upstream"
    make_upstream(upstream)
    make_config(
        upstream,
        skills=[
            {
                "from": "./skills/imported",
                "params": {},
            }
        ],
    )
    git(["add", "-A"], upstream)
    git(["commit", "-qm", "add config"], upstream)

    consumer = tmp_path / "consumer"
    consumer.mkdir()
    make_config(
        consumer,
        sources={"up": {"git": str(upstream), "ref": "main"}},
        extends=["up"],
        skills=[],
    )
    build_and_write(consumer)
    assert "Original." in rendered(consumer, "imported")
