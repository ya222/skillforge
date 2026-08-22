"""Params, anchors and placeholder substitution, end to end through `build`."""

from __future__ import annotations

import pytest

from skillforge.errors import ParamError, SkillError
from skillforge.plan import apply
from skillforge.render import build
from tests.conftest import make_config, make_skill, rendered

LANG_BODY = """
Run {{ params.test_command }} before you finish.

<!-- skillforge:block id=py when='"python" in params.languages' -->
## Python
Use ruff.
<!-- /skillforge:block -->

<!-- skillforge:block id=ts when='"typescript" in params.languages' -->
## TypeScript
Use tsc.
<!-- /skillforge:block -->
"""

PARAMS = {
    "test_command": {"type": "string", "default": "pytest"},
    "languages": {
        "type": "list",
        "items": ["python", "typescript"],
        "default": ["python", "typescript"],
    },
}


def build_and_write(root):
    result = build(root)
    apply(result.plan, root)
    return result


def test_defaults_render_every_block(repo):
    make_skill(repo, params=PARAMS, body=LANG_BODY)
    make_config(repo, skills=[{"from": "./skills/demo"}])
    build_and_write(repo)
    output = rendered(repo, "demo")
    assert "Run pytest before you finish." in output
    assert "## Python" in output
    assert "## TypeScript" in output
    assert "skillforge:block" not in output


def test_when_drops_a_block_and_leaves_no_scar(repo):
    make_skill(repo, params=PARAMS, body=LANG_BODY)
    make_config(repo, shared_params={"languages": ["python"]}, skills=[{"from": "./skills/demo"}])
    build_and_write(repo)
    output = rendered(repo, "demo")
    assert "## Python" in output
    assert "## TypeScript" not in output
    assert "\n\n\n" not in output


def test_per_skill_params_beat_repo_wide_params(repo):
    make_skill(repo, params=PARAMS, body=LANG_BODY)
    make_config(
        repo,
        shared_params={"test_command": "make test"},
        skills=[{"from": "./skills/demo", "params": {"test_command": "cargo test"}}],
    )
    build_and_write(repo)
    assert "Run cargo test before" in rendered(repo, "demo")


def test_shared_param_a_skill_does_not_declare_is_ignored(repo):
    make_skill(repo, params=PARAMS, body=LANG_BODY)
    make_config(repo, shared_params={"unrelated": "value"}, skills=[{"from": "./skills/demo"}])
    build_and_write(repo)
    assert "Run pytest" in rendered(repo, "demo")


def test_undeclared_per_skill_param_is_an_error(repo):
    make_skill(repo, params=PARAMS, body=LANG_BODY)
    make_config(repo, skills=[{"from": "./skills/demo", "params": {"tset_command": "x"}}])
    with pytest.raises(ParamError, match="tset_command"):
        build(repo)


def test_wrong_param_type_is_an_error(repo):
    make_skill(repo, params=PARAMS, body=LANG_BODY)
    make_config(repo, skills=[{"from": "./skills/demo", "params": {"languages": "python"}}])
    with pytest.raises(ParamError, match="expected list"):
        build(repo)


def test_value_outside_a_list_allowlist_is_an_error(repo):
    make_skill(repo, params=PARAMS, body=LANG_BODY)
    make_config(repo, skills=[{"from": "./skills/demo", "params": {"languages": ["cobol"]}}])
    with pytest.raises(ParamError, match="cobol"):
        build(repo)


def test_required_param_without_a_value_is_an_error(repo):
    make_skill(repo, params={"owner": {"type": "string"}}, body="Owned by {{ params.owner }}.\n")
    make_config(repo, skills=[{"from": "./skills/demo"}])
    with pytest.raises(ParamError, match="required"):
        build(repo)


def test_required_param_supplied_as_shared(repo):
    make_skill(repo, params={"owner": {"type": "string"}}, body="Owned by {{ params.owner }}.\n")
    make_config(repo, shared_params={"owner": "platform"}, skills=[{"from": "./skills/demo"}])
    build_and_write(repo)
    assert "Owned by platform." in rendered(repo, "demo")


def test_unknown_placeholder_that_claims_to_be_a_param_is_an_error(repo):
    make_skill(repo, params=PARAMS, body="{{ params.nope }}\n")
    make_config(repo, skills=[{"from": "./skills/demo"}])
    with pytest.raises(ParamError, match="nope"):
        build(repo)


def test_unrelated_braces_pass_through_untouched(repo):
    make_skill(repo, body="Example: {{ sortBy: 'date' }} stays as written.\n")
    make_config(repo, skills=[{"from": "./skills/demo"}])
    build_and_write(repo)
    assert "{{ sortBy: 'date' }}" in rendered(repo, "demo")


def test_when_referencing_an_undeclared_param_is_an_error(repo):
    make_skill(
        repo,
        body="<!-- skillforge:block id=x when='params.ghost' -->\nhi\n<!-- /skillforge:block -->\n",
    )
    make_config(repo, skills=[{"from": "./skills/demo"}])
    with pytest.raises(Exception, match="ghost"):
        build(repo)


def test_unclosed_block_is_an_error(repo):
    make_skill(repo, body="<!-- skillforge:block id=x -->\nhi\n")
    make_config(repo, skills=[{"from": "./skills/demo"}])
    with pytest.raises(SkillError, match="never closed"):
        build(repo)


def test_skill_name_must_match_its_directory(repo):
    directory = make_skill(repo, name="demo")
    text = (directory / "SKILL.md").read_text().replace("name: demo", "name: other")
    (directory / "SKILL.md").write_text(text)
    make_config(repo, skills=[{"from": "./skills/demo"}])
    with pytest.raises(SkillError, match="does not match directory"):
        build(repo)


def test_as_renames_the_rendered_skill(repo):
    make_skill(repo, body="Body.\n")
    make_config(repo, skills=[{"from": "./skills/demo", "as": "renamed"}])
    build_and_write(repo)
    assert "name: renamed" in rendered(repo, "renamed")


def test_a_plain_agent_skill_without_skillforge_metadata_renders(repo):
    directory = repo / "skills" / "plain"
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(
        "---\nname: plain\ndescription: A plain skill. Use when importing foreign libraries.\n"
        "---\n\n## Rules\n\nBe careful.\n"
    )
    make_config(repo, skills=[{"from": "./skills/plain"}])
    build_and_write(repo)
    output = rendered(repo, "plain")
    assert "Be careful." in output
    assert "version: 0.0.0" in output


def test_a_bundled_file_named_skill_md_is_not_dropped(repo):
    directory = make_skill(repo, body="Body.\n")
    (directory / "references").mkdir()
    (directory / "references" / "SKILL.md").write_text(
        "A reference that happens to be named that.\n"
    )
    make_config(repo, skills=[{"from": "./skills/demo"}], targets={})
    build_and_write(repo)
    assert (repo / ".agents/skills/demo/references/SKILL.md").is_file()


def test_a_text_file_that_is_not_utf8_fails_with_a_named_error(repo):
    directory = make_skill(repo, body="Body.\n")
    (directory / "blob.txt").write_bytes(b"\xff\xfe\x00binary")
    make_config(repo, skills=[{"from": "./skills/demo"}], targets={})
    with pytest.raises(SkillError, match="not valid UTF-8"):
        build(repo)
