# Example: three layers

`org` → `team` → `project`. Only the project is built; the two above it are pure configuration
that nothing renders on its own.

Read the three `skillforge.yaml` files in that order. Each is commented and short.

## What each layer contributes

| Layer | Contributes | Visible in the output as |
| --- | --- | --- |
| `org` | The git source, `targets`, `output`, `test_command: make test`, all three `languages`, and a review rule appended to the `verification` block | `targets` and `output` are never restated below, yet the project still renders `.claude/skills/` and `AGENTS.md` |
| `team` | `test_command: pnpm test`, plus context inserted at the `after-overview` point that no other layer claims | The "Platform team convention" blockquote after the overview |
| `project` | `languages: [typescript]`, a per-skill `test_command`, and a forced takeover of the `verification` block | Only the TypeScript language section survives; the checklist ends with the project's rule and not the org's |

The rendered `test_command` is `pnpm test --filter api`: the project's per-skill param beats its
own repo-wide param, which beat the team's, which beat the org's.

## The part worth understanding

The org and the project both patch the `verification` block. That is an error by default, and
the project resolves it with `force: true`.

Forcing **replaces** the earlier layer's patches on that target rather than stacking on top of
them, which is why the org's review rule is absent from the output. If the project wanted to
keep it, it would have to restate it. That is deliberate: an override that silently kept half of
what it overrode would be harder to reason about than one that starts from the base.

To see the failure mode, delete `force: true` from
[`project/skillforge.yaml`](project/skillforge.yaml) and run:

```bash
skillforge build --root examples/layers/project
```

The build stops and names both layers.

## Rebuilding

```bash
skillforge build --root examples/layers/project
```

Reaches the network and needs SSH access to the (currently private) library, so it is not part
of `make ci`.

For a single-layer repository that imports from two sources including one that has never heard
of skillforge, see [`../consumer/`](../consumer/).
