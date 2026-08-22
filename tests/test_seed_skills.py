"""The skills this repository ships, rendered through real configurations."""

from __future__ import annotations

import shutil

from tests.conftest import REPO_ROOT, make_config, rendered
from tests.test_render import build_and_write


def seeded(repo):
    shutil.copytree(REPO_ROOT / "skills", repo / "skills")
    return repo


def test_eli5_defaults_render_the_artifact_variant(repo):
    seeded(repo)
    make_config(repo, skills=[{"from": "./skills/eli5"}], targets={})
    build_and_write(repo)
    output = rendered(repo, "eli5")
    assert "anthropics/claude-plugins-community" in output
    assert "Explain like I'm a 5 year old" in output
    assert "No more than 300 words" in output
    assert "## The artifact" in output
    assert "## The markdown" not in output


def test_a_markdown_project_drops_the_artifact_section(repo):
    seeded(repo)
    make_config(
        repo,
        params={"audience": "an on-call engineer", "medium": "markdown"},
        skills=[{"from": "./skills/eli5", "params": {"max_words": 120}}],
        targets={},
    )
    build_and_write(repo)
    output = rendered(repo, "eli5")
    assert "Explain like I'm an on-call engineer" in output
    assert "No more than 120 words" in output
    assert "## The markdown" in output
    assert "## The artifact" not in output


def test_a_consumer_can_extend_a_shipped_skill_through_its_anchors(repo):
    seeded(repo)
    make_config(
        repo,
        skills=[
            {
                "from": "./skills/eli5",
                "patches": [
                    {
                        "point": "after-intro",
                        "op": "insert",
                        "content": "> Name the real service, never a stand-in.",
                    },
                    {"block": "rules", "op": "append", "content": "- Link the runbook"},
                ],
            }
        ],
        targets={},
    )
    build_and_write(repo)
    output = rendered(repo, "eli5")
    assert "> Name the real service, never a stand-in." in output
    assert output.index("Topic: $ARGUMENTS") < output.index("> Name the real service")
    assert output.index("> Name the real service") < output.index("## Rules")
    assert "- Link the runbook" in output
    assert "<!-- skillforge" not in output


def test_eli12_defaults_use_the_real_name_rule_and_a_higher_word_cap(repo):
    seeded(repo)
    make_config(repo, skills=[{"from": "./skills/eli12"}], targets={})
    build_and_write(repo)
    output = rendered(repo, "eli12")
    assert "Explain like I'm a curious 12 year old" in output
    assert "No more than 1000 words" in output
    assert "Use the real name for things" in output
    assert "## The artifact" in output
    assert "## The markdown" not in output
