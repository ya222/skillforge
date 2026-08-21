# Adapters

An adapter turns the canonical rendered skills (see [concepts.md](concepts.md)) into what one
harness reads. Enable them under `targets:` in [skillforge.yaml](consuming-skills.md).

Adapters never write to disk themselves. They append to the build plan, which is why
`skillforge check` can compare a full build against the working tree without touching it.

## `claude-code`

| Option | Default |
| --- | --- |
| `path` | `.claude/skills` |

Copies each rendered skill directory verbatim. Claude Code discovers Agent Skills natively, so
there is nothing else to wire up.

## `agents-md`

| Option | Default |
| --- | --- |
| `path` | `AGENTS.md` |
| `heading` | `## Agent skills` |

Writes an index of skills, each linking to its rendered `SKILL.md`, into a **managed region**:

```markdown
<!-- skillforge:begin -->
...generated...
<!-- skillforge:end -->
```

Everything outside the markers is yours and is preserved across rebuilds. If the file has no
region yet, one is appended.

This covers every harness that reads `AGENTS.md` and has no native skill loader, including
Codex, Gemini CLI and opencode. Those agents read the index, then open the skill file when its
description matches the task.

## `copilot`

| Option | Default |
| --- | --- |
| `index` | `.github/copilot-instructions.md` |
| `path` | `.github/instructions` |

Writes one `<skill>.instructions.md` per skill with Copilot's `applyTo` frontmatter, taken from
the skill's `globs` (`**` when it declares none), plus a managed index region in
`copilot-instructions.md`.

## `cursor`

| Option | Default |
| --- | --- |
| `path` | `.cursor/rules` |

Writes one `<skill>.mdc` per skill with Cursor's `description`, `globs` and
`alwaysApply: false` frontmatter, so Cursor loads a rule by description rather than always.

## Adding an adapter

1. Write `src/skillforge/adapters/<harness>.py` with
   `apply(skills, config, options, plan) -> None`.
2. Register it in `ADAPTERS` in `src/skillforge/adapters/__init__.py`.
3. Add its name to the `targets` enum in
   [`schema/skillforge.schema.json`](../schema/skillforge.schema.json).
4. Add a test to `tests/test_adapters.py` asserting the harness's real file layout.
5. Document it above.

Append `FileWrite` for files skillforge fully owns, and `RegionWrite` for a managed region in a
file a human also edits. Add any directory you fully own to `plan.managed_dirs` so stale files
are pruned when a skill is removed.
