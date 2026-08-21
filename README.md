# skillforge

A versioned library of portable AI agent skills, plus a composition layer that lets other
repositories import those skills, configure them, extend them, and add their own.

Skills are written once in the open [Agent Skills](https://agentskills.io) directory format
(`SKILL.md` + bundled files). Consumers do not fork them. They declare what they want in a
`skillforge.yaml`, and skillforge renders skills tailored to that repo for every agent harness
the repo uses.

```
skills/<name>/SKILL.md          the base skill, plain and directly usable
        ↓  params, anchors, patches from skillforge.yaml
.agents/skills/<name>/          the rendered artifact, committed
        ↓  adapters
.claude/skills/  AGENTS.md  .github/instructions/  .cursor/rules/
```

## What it is for

An agent skill is usually 90% general and 10% specific to your repo: the test command, the
languages you actually use, the rule your team argued about once. Copying a skill into every
repo means that 90% drifts. Importing it and patching the 10% means it does not.

## Quickstart, as a consumer

```bash
uvx --from git+https://github.com/ya222/skillforge skillforge init
```

Then edit `skillforge.yaml`:

```yaml
version: 1

sources:
  lib: { git: https://github.com/ya222/skillforge, ref: main }

params:
  test_command: pnpm test
  languages: [typescript]

skills:
  - from: lib/code-simplification
    patches:
      - point: after-overview
        op: insert
        content: "> Never simplify anything under `vendor/`."

targets:
  claude-code: {}
  agents-md: {}

output: .agents/skills
```

```bash
uvx --from git+https://github.com/ya222/skillforge skillforge build
git add . && git commit -m "add skillforge skills"
```

Rendered output is committed, so anyone cloning the repo gets working skills without
installing anything. See [docs/consuming-skills.md](docs/consuming-skills.md) for the full
configuration reference.

## Quickstart, as an author

Skills live in [`skills/`](skills/). A base skill is a normal `SKILL.md` that declares its
params and marks the passages consumers are allowed to change. See
[docs/authoring-skills.md](docs/authoring-skills.md).

## Skills in this library

| Skill | What it does |
| --- | --- |
| [`code-simplification`](skills/code-simplification/SKILL.md) | Reduce complexity without changing behavior |
| [`frontend-ui-engineering`](skills/frontend-ui-engineering/SKILL.md) | Build accessible, production-quality UI |
| [`performance-optimization`](skills/performance-optimization/SKILL.md) | Measure, fix and verify performance work |

All three are adapted from [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills)
under the MIT licence; attribution travels with the rendered output.

## Documentation

| Document | For |
| --- | --- |
| [docs/concepts.md](docs/concepts.md) | The model: bases, params, anchors, patches, layers, targets |
| [docs/authoring-skills.md](docs/authoring-skills.md) | Writing a base skill |
| [docs/consuming-skills.md](docs/consuming-skills.md) | `skillforge.yaml` reference |
| [docs/adapters.md](docs/adapters.md) | What each harness gets, and how to add one |
| [docs/cli.md](docs/cli.md) | Command reference |
| [docs/local-ci.md](docs/local-ci.md) | Running CI on your machine |
| [examples/consumer/](examples/consumer/) | A worked consumer repository, built for real |
| [DECISIONS.md](DECISIONS.md) | Why the design is the way it is |
| [TODO.md](TODO.md) | Milestones and what is left |
| [AGENTS.md](AGENTS.md) | Instructions for agents working in this repo |

## Licence

MIT. See [LICENSE](LICENSE).
