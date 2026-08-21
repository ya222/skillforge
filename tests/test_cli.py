"""The commands that mutate configuration rather than render it."""

from __future__ import annotations

import pytest
import yaml
from click.testing import CliRunner
from tests.conftest import make_config, make_skill, rendered
from tests.test_render import build_and_write
from tests.test_sources import make_upstream

from skillforge.cli import main


def run(*args):
    result = CliRunner().invoke(main, list(args), standalone_mode=False)
    if result.exception and not isinstance(result.exception, SystemExit):
        raise result.exception
    return result


def config_of(repo):
    return yaml.safe_load((repo / "skillforge.yaml").read_text())


def test_init_writes_a_starter_config(repo):
    run("init", "--root", str(repo))
    assert config_of(repo)["version"] == 1


def test_init_refuses_to_clobber(repo):
    run("init", "--root", str(repo))
    with pytest.raises(Exception, match="already exists"):
        run("init", "--root", str(repo))


def test_add_appends_an_entry(repo):
    run("init", "--root", str(repo))
    run("add", "lib/code-simplification", "--root", str(repo))
    assert config_of(repo)["skills"] == [{"from": "lib/code-simplification"}]


def test_add_respects_an_alias_and_rejects_duplicates(repo):
    run("init", "--root", str(repo))
    run("add", "lib/code-simplification", "--as", "simplify", "--root", str(repo))
    assert config_of(repo)["skills"][0]["as"] == "simplify"
    with pytest.raises(Exception, match="already configured"):
        run("add", "lib/other", "--as", "simplify", "--root", str(repo))


def test_eject_copies_the_skill_local_and_repoints_the_config(tmp_path):
    upstream = tmp_path / "upstream"
    make_upstream(upstream)
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    make_config(
        consumer,
        sources={"up": {"git": str(upstream), "ref": "main"}},
        skills=[
            {
                "from": "up/imported",
                "patches": [{"heading": "Upstream", "op": "remove", "upstream_hash": "sha256:x"}],
            }
        ],
    )
    run("eject", "imported", "--root", str(consumer))

    assert (consumer / "skills" / "imported" / "SKILL.md").is_file()
    entry = config_of(consumer)["skills"][0]
    assert entry["from"] == "./skills/imported"
    assert "patches" not in entry

    build_and_write(consumer)
    assert "Original." in rendered(consumer, "imported")


def test_eject_refuses_a_skill_that_is_already_local(repo):
    make_skill(repo, body="Body.\n")
    make_config(repo, skills=[{"from": "./skills/demo"}])
    with pytest.raises(Exception, match="already local"):
        run("eject", "demo", "--root", str(repo))


def test_check_fails_when_output_is_stale(repo):
    make_skill(repo, body="Body.\n")
    make_config(repo, skills=[{"from": "./skills/demo"}], targets={})
    with pytest.raises(Exception, match="out of date"):
        run("check", "--root", str(repo))
