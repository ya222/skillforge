"""Layering via `extends`, including the force rule for conflicting patches."""

from __future__ import annotations

import pytest
import yaml

from skillforge.errors import ConfigError, PatchError
from skillforge.render import build
from tests.conftest import make_config, make_skill, rendered
from tests.test_render import build_and_write

BODY = """
<!-- skillforge:block id=rules -->
- Base rule.
<!-- /skillforge:block -->
"""


def make_layer(root, name, config):
    directory = root / name
    directory.mkdir(parents=True, exist_ok=True)
    config.setdefault("version", 1)
    (directory / "skillforge.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
    return directory


def test_extends_pulls_skills_and_params_from_a_parent_layer(repo):
    make_skill(repo, params={"owner": {"type": "string", "default": "nobody"}}, body=BODY)
    make_layer(
        repo,
        "org",
        {
            "shared_params": {"owner": "platform"},
            "skills": [{"from": "../skills/demo"}],
        },
    )
    make_config(repo, extends=["./org"], skills=[])
    build_and_write(repo)
    assert "- Base rule." in rendered(repo, "sf-demo")


def test_a_later_layer_overrides_a_param(repo):
    make_skill(
        repo,
        params={"owner": {"type": "string", "default": "nobody"}},
        body="Owner: {{ params.owner }}\n",
    )
    make_layer(
        repo,
        "org",
        {"shared_params": {"owner": "platform"}, "skills": [{"from": "../skills/demo"}]},
    )
    make_config(repo, extends=["./org"], shared_params={"owner": "project-x"}, skills=[])
    build_and_write(repo)
    assert "Owner: project-x" in rendered(repo, "sf-demo")


def test_two_layers_patching_one_anchor_is_an_error(repo):
    make_skill(repo, body=BODY)
    make_layer(
        repo,
        "org",
        {
            "skills": [
                {
                    "from": "../skills/demo",
                    "patches": [{"block": "rules", "op": "replace", "content": "- Org rule."}],
                }
            ]
        },
    )
    make_config(
        repo,
        extends=["./org"],
        skills=[
            {
                "from": "./skills/demo",
                "patches": [{"block": "rules", "op": "replace", "content": "- Project rule."}],
            }
        ],
    )
    with pytest.raises(PatchError, match="force: true"):
        build(repo)


def test_force_lets_the_later_layer_win(repo):
    make_skill(repo, body=BODY)
    make_layer(
        repo,
        "org",
        {
            "skills": [
                {
                    "from": "../skills/demo",
                    "patches": [{"block": "rules", "op": "replace", "content": "- Org rule."}],
                }
            ]
        },
    )
    make_config(
        repo,
        extends=["./org"],
        skills=[
            {
                "from": "./skills/demo",
                "patches": [
                    {
                        "block": "rules",
                        "op": "replace",
                        "content": "- Project rule.",
                        "force": True,
                    }
                ],
            }
        ],
    )
    build_and_write(repo)
    output = rendered(repo, "sf-demo")
    assert "- Project rule." in output
    assert "- Org rule." not in output


def test_two_patches_in_one_layer_both_apply(repo):
    make_skill(repo, body=BODY)
    make_config(
        repo,
        skills=[
            {
                "from": "./skills/demo",
                "patches": [
                    {"block": "rules", "op": "append", "content": "- One."},
                    {"block": "rules", "op": "append", "content": "- Two."},
                ],
            }
        ],
    )
    build_and_write(repo)
    output = rendered(repo, "sf-demo")
    assert "- One." in output and "- Two." in output


def test_the_same_name_from_two_different_sources_is_an_error(repo):
    make_skill(repo, name="demo", body=BODY)
    make_skill(repo, name="other", body=BODY)
    make_layer(repo, "org", {"skills": [{"from": "../skills/other", "as": "demo"}]})
    make_config(repo, extends=["./org"], skills=[{"from": "./skills/demo"}])
    with pytest.raises(ConfigError, match="disambiguate"):
        build(repo)


def test_circular_extends_is_an_error(repo):
    make_skill(repo, body=BODY)
    make_layer(repo, "org", {"extends": ["../skillforge.yaml"], "skills": []})
    make_config(repo, extends=["./org"], skills=[{"from": "./skills/demo"}])
    with pytest.raises(ConfigError, match="circular"):
        build(repo)


def test_targets_and_output_survive_two_levels_of_extends(repo):
    make_skill(repo, body=BODY)
    make_layer(
        repo,
        "org",
        {
            "skills": [{"from": "../skills/demo"}],
            "targets": {"claude-code": {}, "cursor": {}},
            "output": "rendered/skills",
        },
    )
    make_layer(repo, "team", {"extends": ["../org"]})
    # Not make_config: that helper always writes a `targets` key, which would
    # override the org layer and hide what this test is about.
    make_layer(repo, ".", {"extends": ["./team"], "skills": []})
    build_and_write(repo)
    assert (repo / "rendered/skills/sf-demo/SKILL.md").is_file()
    assert (repo / ".claude/skills/sf-demo/SKILL.md").is_file()
    assert (repo / ".cursor/rules/sf-demo.mdc").is_file()


def test_a_diamond_of_layers_is_not_a_cycle(repo):
    """project -> (teamA, teamB) -> org. The shared layer contributes once."""
    make_skill(repo, body=BODY)
    make_layer(
        repo,
        "org",
        {
            "skills": [
                {
                    "from": "../skills/demo",
                    "patches": [{"block": "rules", "op": "append", "content": "- Org rule."}],
                }
            ]
        },
    )
    make_layer(repo, "teamA", {"extends": ["../org"]})
    make_layer(repo, "teamB", {"extends": ["../org"]})
    make_config(repo, extends=["./teamA", "./teamB"], skills=[])
    build_and_write(repo)
    assert rendered(repo, "sf-demo").count("- Org rule.") == 1


def test_a_real_cycle_names_the_chain(repo):
    make_skill(repo, body=BODY)
    make_layer(repo, "org", {"extends": ["../skillforge.yaml"], "skills": []})
    make_config(repo, extends=["./org"], skills=[{"from": "./skills/demo"}])
    with pytest.raises(ConfigError, match="circular `extends` chain"):
        build(repo)
