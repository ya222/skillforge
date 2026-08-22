# Adapters

An adapter turns the canonical rendered skills (see [concepts.md](concepts.md)) into what one
harness reads. Enable them under `targets:` in [skillforge.yaml](consuming-skills.md).

Adapters never write to disk themselves. They append to the build plan, which is why
`skillforge check` can compare a full build against the working tree without touching it.

## `claude-code`

| Option | Default |
| --- | --- |
| `path` | `.claude/skills` |
| `user` | `false` |

Copies each rendered skill directory verbatim. Claude Code discovers Agent Skills natively, so
there is nothing else to wire up.

`user: true` writes to `~/.claude/skills/` instead, which Claude Code loads in every project on
that machine. It cannot be combined with `path`. Only the `sf-` entries there are touched, so
skills you wrote by hand alongside them are safe. `skillforge check` verifies that scope like
any other and reports what is missing or modified; it never writes.

The lockfile then records files in the home directory of whoever ran the build. On a machine
that has not run `skillforge build`, `check` reports them as missing and fails, and so does
`make ci` or the pre-commit hook in a repo that runs it. That is intended: the user scope is
verified, not assumed. In a shared repository, either every contributor runs `skillforge build`
once after cloning, or keep `user: true` to a personal config outside the shared one.

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

Append `FileWrite` for files skillforge owns, and `RegionWrite` for a managed region in a file
a human also edits. Name every file after the rendered skill, so it carries the `sf-` prefix,
and add its directory to `plan.managed_dirs`: pruning only ever removes `sf-` entries that the
current build did not produce, so a directory is safe to manage even when it also holds
hand-written files.
