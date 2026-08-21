"""Patching: anchors, heading escape hatch, hash pinning, layer conflicts."""

from __future__ import annotations

import hashlib

import pytest

from skillforge.errors import ConfigError, PatchError
from skillforge.render import build
from tests.conftest import make_config, make_skill, rendered
from tests.test_render import build_and_write

BODY = """
## Overview

Original overview.

<!-- skillforge:point id=after-overview -->

<!-- skillforge:block id=rules -->
## Rules

- Original rule.
<!-- /skillforge:block -->

## Verification

- [ ] Original check.
"""


def section_hash(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode()).hexdigest()}"


def test_replace_a_block(repo):
    make_skill(repo, body=BODY)
    make_config(
        repo,
        skills=[
            {
                "from": "./skills/demo",
                "patches": [
                    {"block": "rules", "op": "replace", "content": "## Rules\n\n- House rule.\n"}
                ],
            }
        ],
    )
    build_and_write(repo)
    output = rendered(repo, "demo")
    assert "- House rule." in output
    assert "- Original rule." not in output


def test_append_and_prepend_a_block(repo):
    make_skill(repo, body=BODY)
    make_config(
        repo,
        skills=[
            {
                "from": "./skills/demo",
                "patches": [
                    {"block": "rules", "op": "append", "content": "- Appended rule."},
                    {"block": "rules", "op": "prepend", "content": "- Prepended rule."},
                ],
            }
        ],
    )
    build_and_write(repo)
    output = rendered(repo, "demo")
    assert output.index("- Prepended rule.") < output.index("- Original rule.")
    assert output.index("- Original rule.") < output.index("- Appended rule.")


def test_remove_a_block(repo):
    make_skill(repo, body=BODY)
    make_config(
        repo,
        skills=[{"from": "./skills/demo", "patches": [{"block": "rules", "op": "remove"}]}],
    )
    build_and_write(repo)
    output = rendered(repo, "demo")
    assert "## Rules" not in output
    assert "## Verification" in output


def test_insert_at_a_point(repo):
    make_skill(repo, body=BODY)
    make_config(
        repo,
        skills=[
            {
                "from": "./skills/demo",
                "patches": [
                    {"point": "after-overview", "op": "insert", "content": "House context here."}
                ],
            }
        ],
    )
    build_and_write(repo)
    output = rendered(repo, "demo")
    assert output.index("Original overview.") < output.index("House context here.")
    assert output.index("House context here.") < output.index("## Rules")


def test_patching_an_unknown_block_names_the_available_ones(repo):
    make_skill(repo, body=BODY)
    make_config(
        repo,
        skills=[{"from": "./skills/demo", "patches": [{"block": "ghost", "op": "remove"}]}],
    )
    with pytest.raises(PatchError, match="available: rules"):
        build(repo)


def test_heading_patch_requires_a_pinned_hash(repo):
    make_skill(repo, body=BODY)
    make_config(
        repo,
        skills=[
            {
                "from": "./skills/demo",
                "patches": [{"heading": "Verification", "op": "append", "content": "- Extra."}],
            }
        ],
    )
    with pytest.raises(ConfigError, match="upstream_hash"):
        build(repo)


def test_heading_patch_applies_when_the_hash_matches(repo):
    make_skill(repo, body=BODY)
    pinned = section_hash("## Verification\n\n- [ ] Original check.\n")
    make_config(
        repo,
        skills=[
            {
                "from": "./skills/demo",
                "patches": [
                    {
                        "heading": "Verification",
                        "op": "append",
                        "content": "- [ ] Extra check.",
                        "upstream_hash": pinned,
                    }
                ],
            }
        ],
    )
    build_and_write(repo)
    assert "- [ ] Extra check." in rendered(repo, "demo")


def test_heading_patch_fails_loudly_when_upstream_moved(repo):
    make_skill(repo, body=BODY)
    make_config(
        repo,
        skills=[
            {
                "from": "./skills/demo",
                "patches": [
                    {
                        "heading": "Verification",
                        "op": "append",
                        "content": "- [ ] Extra check.",
                        "upstream_hash": "sha256:" + "0" * 64,
                    }
                ],
            }
        ],
    )
    with pytest.raises(PatchError, match="has changed"):
        build(repo)


def test_heading_not_found_lists_what_is_available(repo):
    make_skill(repo, body=BODY)
    make_config(
        repo,
        skills=[
            {
                "from": "./skills/demo",
                "patches": [
                    {
                        "heading": "Nowhere",
                        "op": "remove",
                        "upstream_hash": "sha256:" + "0" * 64,
                    }
                ],
            }
        ],
    )
    with pytest.raises(PatchError, match="Available headings"):
        build(repo)


def test_headings_inside_code_fences_are_not_targets(repo):
    body = "## Real\n\n```python\n# comment\n## not a heading\n```\n"
    make_skill(repo, body=body)
    pinned = section_hash(body)
    make_config(
        repo,
        skills=[
            {
                "from": "./skills/demo",
                "patches": [
                    {"heading": "Real", "op": "append", "content": "Tail.", "upstream_hash": pinned}
                ],
            }
        ],
    )
    build_and_write(repo)
    assert "Tail." in rendered(repo, "demo")


def test_add_and_remove_files(repo):
    directory = make_skill(repo, body=BODY)
    (directory / "references").mkdir()
    (directory / "references" / "old.md").write_text("old\n")
    make_config(
        repo,
        skills=[
            {
                "from": "./skills/demo",
                "patches": [
                    {"op": "remove-file", "file": "references/old.md"},
                    {"op": "add-file", "file": "references/new.md", "content": "new\n"},
                ],
            }
        ],
    )
    build_and_write(repo)
    output = repo / ".agents/skills/demo/references"
    assert not (output / "old.md").exists()
    assert (output / "new.md").read_text() == "new\n"


def test_set_frontmatter(repo):
    make_skill(repo, body=BODY)
    make_config(
        repo,
        skills=[
            {
                "from": "./skills/demo",
                "patches": [
                    {
                        "op": "set-frontmatter",
                        "key": "description",
                        "content": "Rewritten. Use when testing.",
                    }
                ],
            }
        ],
    )
    build_and_write(repo)
    assert "description: Rewritten. Use when testing." in rendered(repo, "demo")


def test_a_heading_after_a_deeper_one_is_not_nested_under_it(repo):
    """A document that jumps from h3 back to h2 must not nest the h2."""
    body = "### Deep\n\ntext\n\n## Shallow\n\nmore\n"
    make_skill(repo, body=body)
    pinned = section_hash("## Shallow\n\nmore\n")
    make_config(
        repo,
        skills=[
            {
                "from": "./skills/demo",
                "patches": [
                    {
                        "heading": "Shallow",
                        "op": "append",
                        "content": "Tail.",
                        "upstream_hash": pinned,
                    }
                ],
            }
        ],
    )
    build_and_write(repo)
    output = rendered(repo, "demo")
    assert output.index("more") < output.index("Tail.")

    with pytest.raises(PatchError, match="not found"):
        make_config(
            repo,
            skills=[
                {
                    "from": "./skills/demo",
                    "patches": [
                        {
                            "heading": "Deep > Shallow",
                            "op": "remove",
                            "upstream_hash": pinned,
                        }
                    ],
                }
            ],
        )
        build(repo)


def test_two_patches_adding_the_same_file_is_an_error(repo):
    make_skill(repo, body=BODY)
    make_config(
        repo,
        skills=[
            {
                "from": "./skills/demo",
                "patches": [
                    {"op": "add-file", "file": "a.md", "content": "one"},
                    {"op": "add-file", "file": "a.md", "content": "two"},
                ],
            }
        ],
    )
    with pytest.raises(PatchError, match="more than one patch"):
        build(repo)


def test_appending_to_a_block_that_another_patch_removes_is_an_error(repo):
    make_skill(repo, body=BODY)
    make_config(
        repo,
        skills=[
            {
                "from": "./skills/demo",
                "patches": [
                    {"block": "rules", "op": "append", "content": "- Lost rule."},
                    {"block": "rules", "op": "remove"},
                ],
            }
        ],
    )
    with pytest.raises(PatchError, match="would be lost"):
        build(repo)


def test_inserting_at_a_point_inside_a_replaced_block_is_an_error(repo):
    body = (
        "<!-- skillforge:block id=rules -->\n"
        "## Rules\n\n"
        "<!-- skillforge:point id=inside -->\n\n"
        "- Original rule.\n"
        "<!-- /skillforge:block -->\n"
    )
    make_skill(repo, body=body)
    make_config(
        repo,
        skills=[
            {
                "from": "./skills/demo",
                "patches": [
                    {"point": "inside", "op": "insert", "content": "Lost context."},
                    {"block": "rules", "op": "replace", "content": "## Rules\n\n- House rule.\n"},
                ],
            }
        ],
    )
    with pytest.raises(PatchError, match="would be lost"):
        build(repo)


def test_two_inserts_at_one_point_both_apply(repo):
    make_skill(repo, body=BODY)
    make_config(
        repo,
        skills=[
            {
                "from": "./skills/demo",
                "patches": [
                    {"point": "after-overview", "op": "insert", "content": "First."},
                    {"point": "after-overview", "op": "insert", "content": "Second."},
                ],
            }
        ],
    )
    build_and_write(repo)
    output = rendered(repo, "demo")
    assert "First." in output and "Second." in output
