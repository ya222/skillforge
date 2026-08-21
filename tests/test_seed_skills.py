"""The skills this repository ships, rendered through real configurations."""

from __future__ import annotations

import shutil

from tests.conftest import REPO_ROOT, make_config, rendered
from tests.test_render import build_and_write


def seeded(repo):
    shutil.copytree(REPO_ROOT / "skills", repo / "skills")
    return repo


def test_python_only_project_drops_the_other_language_sections(repo):
    seeded(repo)
    make_config(
        repo,
        params={"test_command": "pytest -q", "languages": ["python"]},
        skills=[{"from": "./skills/code-simplification"}],
        targets={},
    )
    build_and_write(repo)
    output = rendered(repo, "code-simplification")
    assert "### Python" in output
    assert "### TypeScript / JavaScript" not in output
    assert "### React / JSX" not in output
    assert "`pytest -q` passes without modifying any test" in output


def test_a_frontend_only_project_drops_backend_anti_patterns(repo):
    seeded(repo)
    make_config(
        repo,
        params={"layers": ["frontend"], "bundle_budget_kb": 120},
        skills=[{"from": "./skills/performance-optimization"}],
        targets={},
    )
    build_and_write(repo)
    output = rendered(repo, "performance-optimization")
    assert "#### Large Bundle Size" in output
    assert "#### Missing Caching (Backend)" not in output
    assert "#### N+1 Queries (Backend)" not in output
    assert "< 120KB gzipped" in output


def test_a_vue_project_drops_the_react_component_patterns(repo):
    seeded(repo)
    make_config(
        repo,
        params={"framework": "vue", "wcag_level": "AAA", "design_system": "our Figma tokens"},
        skills=[{"from": "./skills/frontend-ui-engineering"}],
        targets={},
    )
    build_and_write(repo)
    output = rendered(repo, "frontend-ui-engineering")
    assert "### Component Patterns" not in output
    assert "## Accessibility (WCAG 2.1 AAA)" in output
    assert "Match our Figma tokens." in output


def test_a_consumer_can_extend_a_shipped_skill_through_its_anchors(repo):
    seeded(repo)
    make_config(
        repo,
        skills=[
            {
                "from": "./skills/code-simplification",
                "patches": [
                    {
                        "point": "after-overview",
                        "op": "insert",
                        "content": "> In this repo, never simplify anything under `vendor/`.",
                    },
                    {
                        "block": "verification",
                        "op": "append",
                        "content": "- [ ] `make lint` passes",
                    },
                ],
            }
        ],
        targets={},
    )
    build_and_write(repo)
    output = rendered(repo, "code-simplification")
    assert "never simplify anything under `vendor/`" in output
    assert "- [ ] `make lint` passes" in output
    assert output.index("never simplify") < output.index("## When to Use")
