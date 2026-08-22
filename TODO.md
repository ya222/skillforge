# TODO

Milestones for skillforge. Rationale for the design lives in [DECISIONS.md](DECISIONS.md);
mechanics live in [docs/](docs/). This file tracks only what is done and what is left.

## M0 — Scaffold ✅

- [x] uv project, `hatchling` build, `ruff` and `pytest` config
- [x] MIT licence, `.gitignore` excluding only the source cache
- [x] `Makefile` as the human entrypoint
- [x] Git hooks installer wired to `make ci`
- [x] Documentation skeleton

## M1 — Core render ✅

- [x] `SKILL.md` envelope parse and dump
- [x] Skill model and validation (`name`, `description`, `metadata.skillforge`)
- [x] Param schema, layering and type checking
- [x] `{{ params.x }}` substitution
- [x] Block and point anchors, with unpaired/nested/duplicate detection
- [x] `when` expression parser and evaluator
- [x] Build plan separated from writing, so `check` never touches the tree

## M2 — Composition ✅

- [x] Git source fetching into a gitignored cache
- [x] `skillforge.lock` pinning commits, skill versions and output digests
- [x] Patch ops: replace, append, prepend, insert, remove, add-file, remove-file, set-frontmatter
- [x] Heading-path targeting with mandatory `upstream_hash`, fence-aware
- [x] `extends` layering, with the conflict/`force` rule
- [x] Drift detection and pruning of stale generated files
- [x] `eject`

## M3 — Adapters ✅

- [x] `claude-code`
- [x] `agents-md` (Codex, Gemini CLI, opencode) with managed regions
- [x] `copilot`
- [x] `cursor`

## M4 — Seed content ✅

- [x] `eli5` vendored, anchored and parameterised
- [x] The repository self-hosts: it builds its own skills with its own tool
- [x] Skill linter with the rules in [docs/authoring-skills.md](docs/authoring-skills.md)

## M5 — Proof ✅

- [x] `examples/consumer/` importing this library over git
- [x] The same example importing `anthropics/claude-plugins-community` live and patching it by
      hash-pinned heading path
- [x] A second example showing three-layer `extends` (org → team → project)

## M6 — Ship ⏳

- [x] JSON Schema for `skillforge.yaml`
- [x] README, AGENTS.md, docs, DECISIONS.md
- [x] Tag `v0.1.0`
- [ ] Decide whether the repository goes public (currently private)

## Backlog

Not scheduled. Each needs a decision before it is built.

- [ ] `skillforge diff <skill>` — show the rendered result against the untouched base
- [ ] Adapters for further harnesses as they gain skill support
- [ ] `requires:` between skills, so importing one pulls its dependencies
- [ ] Verify that `update` reports which patches now target changed upstream sections, rather
      than only failing on the next build
- [ ] Skill-level `allowed-tools` passthrough tests
- [ ] Support for commands, subagents and hooks alongside skills. Deliberately out of scope for
      v1; the output layout leaves room
