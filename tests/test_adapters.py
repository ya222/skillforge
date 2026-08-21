"""Each harness adapter writes what that harness actually reads."""

from __future__ import annotations

from tests.conftest import make_config, make_skill
from tests.test_render import build_and_write

BODY = "## Rules\n\nBe careful.\n"


def setup(repo, targets):
    make_skill(repo, body=BODY, globs=["**/*.py"])
    make_config(repo, skills=[{"from": "./skills/demo"}], targets=targets)
    build_and_write(repo)


def test_claude_code_copies_the_skill_directory(repo):
    setup(repo, {"claude-code": {}})
    output = (repo / ".claude/skills/demo/SKILL.md").read_text()
    assert "name: demo" in output
    assert "Be careful." in output


def test_agents_md_writes_a_managed_region_and_keeps_the_rest(repo):
    (repo / "AGENTS.md").write_text("# House rules\n\nHand written.\n")
    setup(repo, {"agents-md": {}})
    output = (repo / "AGENTS.md").read_text()
    assert "Hand written." in output
    assert "skillforge:begin" in output
    assert "(.agents/skills/demo/SKILL.md)" in output


def test_agents_md_rebuild_replaces_only_the_region(repo):
    (repo / "AGENTS.md").write_text("# House rules\n\nHand written.\n")
    setup(repo, {"agents-md": {}})
    (repo / "AGENTS.md").write_text(
        (repo / "AGENTS.md").read_text() + "\n## Trailing section\n\nAlso hand written.\n"
    )
    build_and_write(repo)
    output = (repo / "AGENTS.md").read_text()
    assert output.count("skillforge:begin") == 1
    assert "Hand written." in output
    assert "Also hand written." in output


def test_copilot_writes_instruction_files_with_apply_to(repo):
    import yaml

    setup(repo, {"copilot": {}})
    instructions = (repo / ".github/instructions/demo.instructions.md").read_text()
    assert yaml.safe_load(instructions.split("---")[1])["applyTo"] == "**/*.py"
    assert "Be careful." in instructions
    assert "`demo`" in (repo / ".github/copilot-instructions.md").read_text()


def test_cursor_writes_one_mdc_per_skill(repo):
    import yaml

    setup(repo, {"cursor": {}})
    front = yaml.safe_load((repo / ".cursor/rules/demo.mdc").read_text().split("---")[1])
    assert front["globs"] == "**/*.py"
    assert front["alwaysApply"] is False


def test_removing_a_skill_prunes_its_generated_files(repo):
    setup(repo, {"claude-code": {}, "cursor": {}})
    assert (repo / ".claude/skills/demo/SKILL.md").exists()
    make_config(repo, skills=[], targets={"claude-code": {}, "cursor": {}})
    make_skill(repo, name="other", body=BODY)
    make_config(
        repo, skills=[{"from": "./skills/other"}], targets={"claude-code": {}, "cursor": {}}
    )
    build_and_write(repo)
    assert not (repo / ".claude/skills/demo").exists()
    assert not (repo / ".cursor/rules/demo.mdc").exists()
    assert (repo / ".claude/skills/other/SKILL.md").exists()


TRICKY = "Reviews code: carefully. Use when reviewing 'quoted' things & #tags."


def test_cursor_frontmatter_survives_a_colon_in_the_description(repo):
    import yaml

    make_skill(repo, description=TRICKY, body=BODY, globs=["**/*.py"])
    make_config(repo, skills=[{"from": "./skills/demo"}], targets={"cursor": {}})
    build_and_write(repo)
    front = (repo / ".cursor/rules/demo.mdc").read_text().split("---")[1]
    assert yaml.safe_load(front)["description"] == TRICKY


def test_copilot_frontmatter_survives_a_colon_in_the_description(repo):
    import yaml

    make_skill(repo, description=TRICKY, body=BODY, globs=["**/*.py"])
    make_config(repo, skills=[{"from": "./skills/demo"}], targets={"copilot": {}})
    build_and_write(repo)
    text = (repo / ".github/instructions/demo.instructions.md").read_text()
    assert yaml.safe_load(text.split("---")[1])["description"] == TRICKY


def test_a_multi_line_description_stays_on_one_line_in_the_index(repo):
    make_skill(repo, description="One. Use when testing.\nTwo.", body=BODY)
    make_config(repo, skills=[{"from": "./skills/demo"}], targets={"agents-md": {}})
    build_and_write(repo)
    bullets = [
        line for line in (repo / "AGENTS.md").read_text().splitlines() if line.startswith("- [")
    ]
    assert bullets == ["- [`demo`](.agents/skills/demo/SKILL.md) — One. Use when testing. Two."]
