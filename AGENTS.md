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

- [`sf-architect-review`](.agents/skills/sf-architect-review/SKILL.md) — Reviews system designs and code changes for architectural integrity, scalability, and maintainability, drawing on clean architecture, microservices, event-driven systems, and DDD. Use when reviewing an architecture or a major design change, assessing the impact of a proposed change on scalability or resilience, or checking a design against established patterns.
- [`sf-architecture-designer`](.agents/skills/sf-architecture-designer/SKILL.md) — Use when designing new high-level system architecture, reviewing existing designs, or making architectural decisions. Invoke to create architecture diagrams, write Architecture Decision Records (ADRs), evaluate technology trade-offs, design component interactions, and plan for scalability. Use for system design, architecture review, microservices structuring, ADR authoring, scalability planning, and infrastructure pattern selection — distinct from code-level design patterns or database-only design tasks.
- [`sf-claude-session-limits`](.agents/skills/sf-claude-session-limits/SKILL.md) — Reports this Claude Code session's usage against its Claude.ai Pro/Max limits, the rolling 5-hour session window and the 7-day weekly window. Use when the user types /sf-claude-session-limits or asks how much of their usage, session, rate limit, or weekly quota is left, or when it resets.
- [`sf-cloudflare-quick-tunnel`](.agents/skills/sf-cloudflare-quick-tunnel/SKILL.md) — Expose a local server on a public HTTPS URL with a Cloudflare quick tunnel (TryCloudflare), no account or DNS needed. Use when someone wants to share localhost, give a reviewer or phone a link to a dev server, receive a webhook or OAuth callback locally, or asks about cloudflared, trycloudflare.com, or an ngrok alternative.
- [`sf-dev-style`](.agents/skills/sf-dev-style/SKILL.md) — Writes and edits developer documentation in the Google developer documentation style. Use when writing or reviewing READMEs, guides, tutorials, API references, UI procedures, release notes, error messages, or any prose aimed at developers, and when asked to make docs clearer, more consistent, or more accessible.
- [`sf-eli12`](.agents/skills/sf-eli12/SKILL.md) — Explain a topic like I'm a 12 year old. Use when the user types /sf-eli12 <topic> or asks for an explainer that uses real words but assumes no background, with pictures that show cause and effect.
- [`sf-eli5`](.agents/skills/sf-eli5/SKILL.md) — Explain a topic like I'm a 5 year old. Use when the user types /sf-eli5 <topic> or asks for a dead-simple picture explainer of how something works.
- [`sf-frontend-design`](.agents/skills/sf-frontend-design/SKILL.md) — Guidance for distinctive, intentional visual design when building new UI or reshaping an existing one. Use when building pages, components, landing pages, dashboards, or any interface that should not read as a templated default; covers aesthetic direction, typography, layout, motion, and UI copy.
- [`sf-grill-me`](.agents/skills/sf-grill-me/SKILL.md) — Interviews the user relentlessly about a plan, decision, or idea until nothing is left silently assumed. Use when the user types /sf-grill-me, asks to be grilled, or wants a plan or design stress-tested before any work starts.
- [`sf-handoff`](.agents/skills/sf-handoff/SKILL.md) — Compacts the current conversation into a handoff document that a fresh agent can pick up from. Use when the user types /sf-handoff, is running out of context, is about to stop for the day, or wants to move the work to a new session.
- [`sf-isometric-system-map`](.agents/skills/sf-isometric-system-map/SKILL.md) — Draws an isometric system map of a codebase's infrastructure, with legend and explainer panel. Use when the user types /sf-isometric-system-map or asks for a visual map of how the system's parts connect.
- [`sf-markdown-kanban`](.agents/skills/sf-markdown-kanban/SKILL.md) — Create, inspect, and update project todo boards that use the Markdown Kanban heading and task-property format. Use when a project tracks work in TODO.md, *.todo.md, or *.kanban.md files; when moving tasks between status columns; when adding task metadata or checklist steps; or when a repository may contain multiple independent Markdown todo boards.
- [`sf-skill-creator`](.agents/skills/sf-skill-creator/SKILL.md) — Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, edit, or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy.
<!-- skillforge:end -->
