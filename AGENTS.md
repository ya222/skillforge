# Working in this repository

skillforge is a library of portable AI agent skills plus the tool that composes them into other
repositories. Start with [README.md](README.md) for what it is,
[docs/concepts.md](docs/concepts.md) for the model, and [DECISIONS.md](DECISIONS.md) for why.

**Trust these documents over your memory.** They are kept current on purpose so that any agent
picking this up cold has everything it needs. If you change behaviour, change the document that
describes it in the same commit.

## Map

| Path | What lives there |
| --- | --- |
| `src/skillforge/` | The tool |
| `src/skillforge/adapters/` | The only code that knows a harness exists |
| `skills/` | The base skills this library publishes |
| `tests/` | Integration-style suites that build real repos in temp dirs |
| `docs/` | Reference documentation, one topic per file |
| `schema/` | JSON Schema for `skillforge.yaml` |
| `examples/` | Consumer repositories that prove the tool works |
| `.agents/`, `.claude/` | Generated. Never edit by hand |

Reading order for the tool: `model.py` (what everything is) → `render.py` (the pipeline) →
`plan.py` (what gets written) → the module for whatever you are changing.

## Invariants

Break one of these and the design stops holding.

1. **Params are values, anchors are structure.** Never add logic to `{{ }}`. Never add a
   structural operation to the param system. (DECISIONS 3)
2. **Nothing degrades quietly.** A missing anchor, unknown param, drifted heading or absent ref
   raises a named error from `errors.py`. No fallbacks, no silent no-ops. (DECISIONS 14)
3. **Adapters do not touch the filesystem.** They append to the plan. This is what lets `check`
   compare a full build against the tree without writing. (docs/adapters.md)
4. **Generated output is committed and verified.** `make check` must pass. (DECISIONS 5)
5. **The `when` language stays tiny.** Parsed, never `eval`'d. If a skill needs more logic, it
   needs two blocks. (docs/authoring-skills.md)
6. **The repo builds its own skills with its own tool.** `skillforge.yaml` at the root is not a
   fixture.

## Workflow

```bash
make setup     # once
make hooks     # once, installs the local CI gate
make ci        # lint, test, check — must pass before every commit
```

There is no hosted CI. See [docs/local-ci.md](docs/local-ci.md).

After changing anything under `skills/` or `skillforge.yaml`, run `make build` and commit the
regenerated files in the same commit.

## Adding things

| To add | Read |
| --- | --- |
| A skill | [docs/authoring-skills.md](docs/authoring-skills.md) |
| A harness adapter | [docs/adapters.md](docs/adapters.md), "Adding an adapter" |
| A patch op | `model.PATCH_OPS`, `patch.apply_patches`, the schema, docs/consuming-skills.md |
| A CLI command | `cli.py`, then [docs/cli.md](docs/cli.md) |

## Conventions

- Errors name the file, the skill and the target. Someone reading only the error should know
  what to open.
- Docstrings explain why a module exists, not what each line does.
- No fact appears in two documents. Cross-reference instead.
- What is left to do lives in [TODO.md](TODO.md), not in code comments.

<!-- skillforge:begin -->
## Agent skills

Read the linked file in full before acting on a skill. Load a skill when its description matches the task at hand.

- [`eli12`](.agents/skills/eli12/SKILL.md) — Explain a topic like I'm a 12 year old. Use when the user types /eli12 <topic> or asks for an explainer that uses real words but assumes no background, with pictures that show cause and effect.
- [`eli5`](.agents/skills/eli5/SKILL.md) — Explain a topic like I'm a 5 year old. Use when the user types /eli5 <topic> or asks for a dead-simple picture explainer of how something works.
- [`isometric-system-map`](.agents/skills/isometric-system-map/SKILL.md) — Draws an isometric system map of a codebase's infrastructure, with legend and explainer panel. Use when the user types /isometric-system-map or asks for a visual map of how the system's parts connect.
<!-- skillforge:end -->
