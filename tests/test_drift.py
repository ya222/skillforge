"""Committed output is verified, not trusted."""

from __future__ import annotations

import pytest

from skillforge import lock as lock_module
from skillforge.errors import DriftError
from skillforge.plan import diff
from skillforge.render import build
from tests.conftest import make_config, make_skill
from tests.test_render import build_and_write


def setup(repo):
    make_skill(repo, body="## Rules\n\nBe careful.\n")
    make_config(repo, skills=[{"from": "./skills/demo"}], targets={"claude-code": {}})
    result = build_and_write(repo)
    lock_module.dump(result.lock, repo)
    return result


def test_a_fresh_build_is_clean(repo):
    setup(repo)
    assert diff(build(repo).plan, repo) == []


def test_hand_editing_generated_output_is_detected(repo):
    setup(repo)
    target = repo / ".agents/skills/sf-demo/SKILL.md"
    target.write_text(target.read_text() + "\nSnuck in.\n")
    assert diff(build(repo).plan, repo) == [
        ".agents/skills/sf-demo/SKILL.md".join(["modified: ", ""])
    ]


def test_deleting_generated_output_is_detected(repo):
    setup(repo)
    (repo / ".claude/skills/sf-demo/SKILL.md").unlink()
    assert "missing: .claude/skills/sf-demo/SKILL.md" in diff(build(repo).plan, repo)


def test_an_orphaned_sf_entry_in_a_managed_directory_is_stale(repo):
    setup(repo)
    (repo / ".agents/skills/sf-old").mkdir()
    (repo / ".agents/skills/sf-old/SKILL.md").write_text("left behind\n")
    assert "stale: .agents/skills/sf-old/SKILL.md" in diff(build(repo).plan, repo)


def test_a_hand_written_skill_in_a_managed_directory_is_not_skillforge_business(repo):
    setup(repo)
    (repo / ".claude/skills/mine").mkdir()
    (repo / ".claude/skills/mine/SKILL.md").write_text("---\nname: mine\n---\n")
    assert diff(build(repo).plan, repo) == []
    build_and_write(repo)
    assert (repo / ".claude/skills/mine/SKILL.md").is_file()


def test_the_lock_records_source_hashes_and_versions(repo):
    result = setup(repo)
    entry = result.lock.skills["sf-demo"]
    assert entry["version"] == "1.0.0"
    assert entry["source_hash"].startswith("sha256:")
    assert lock_module.load(repo).outputs == result.lock.outputs


def test_a_broken_managed_region_is_reported(repo):
    make_skill(repo, body="Body.\n")
    make_config(repo, skills=[{"from": "./skills/demo"}], targets={"agents-md": {}})
    build_and_write(repo)
    (repo / "AGENTS.md").write_text("<!-- skillforge:begin -->\nno end marker\n")
    with pytest.raises(DriftError, match="no matching"):
        diff(build(repo).plan, repo)
