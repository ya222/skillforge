"""Lint catches skill authoring mistakes before a consumer ever sees them."""

from __future__ import annotations

import pytest
from tests.conftest import make_skill

from skillforge.errors import SkillError
from skillforge.lint import lint_skill, lint_tree


def test_a_clean_skill_lints_without_warnings(repo):
    directory = make_skill(
        repo,
        params={"cmd": {"type": "string", "default": "pytest"}},
        body="Run {{ params.cmd }}.\n",
    )
    assert lint_skill(directory) == []


def test_a_description_without_a_trigger_warns(repo):
    directory = make_skill(repo, description="Simplifies code.")
    assert any("when to use" in warning for warning in lint_skill(directory))


def test_an_unused_param_warns(repo):
    directory = make_skill(repo, params={"cmd": {"type": "string", "default": "pytest"}})
    assert any("never used" in warning for warning in lint_skill(directory))


def test_an_undeclared_param_in_the_body_is_an_error(repo):
    directory = make_skill(repo, body="Run {{ params.ghost }}.\n")
    with pytest.raises(SkillError, match="ghost"):
        lint_skill(directory)


def test_a_block_testing_an_undeclared_param_is_an_error(repo):
    directory = make_skill(
        repo,
        body="<!-- skillforge:block id=x when='params.ghost' -->\nhi\n<!-- /skillforge:block -->\n",
    )
    with pytest.raises(SkillError, match="ghost"):
        lint_skill(directory)


def test_a_broken_relative_link_is_an_error(repo):
    directory = make_skill(repo, body="See [the reference](references/missing.md).\n")
    with pytest.raises(SkillError, match="link target"):
        lint_skill(directory)


def test_a_working_relative_link_passes(repo):
    directory = make_skill(repo, body="See [the reference](references/there.md).\n")
    (directory / "references").mkdir()
    (directory / "references" / "there.md").write_text("hi\n")
    assert lint_skill(directory) == []


def test_a_missing_version_is_an_error(repo):
    directory = make_skill(repo)
    path = directory / "SKILL.md"
    path.write_text(path.read_text().replace("version: 1.0.0", "version: one"))
    with pytest.raises(SkillError, match="MAJOR.MINOR.PATCH"):
        lint_skill(directory)


def test_the_shipped_skills_lint_clean():
    from tests.conftest import REPO_ROOT

    assert lint_tree(REPO_ROOT / "skills") == []
