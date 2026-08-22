# Example: three layers

`org` → `team` → `project`. Only the project is built; the two above it are pure configuration
that nothing renders on its own.

Read the three `skillforge.yaml` files in that order. Each is commented and short.

## What each layer contributes

| Layer | Contributes | Visible in the output as |
| --- | --- | --- |
| `org` | The git source, `targets`, `output`, `audience`, `max_words: 300`, and a customer-data rule appended to the `rules` block | `targets` and `output` are never restated below, yet the project still renders `.claude/skills/` and `AGENTS.md` |
| `team` | `max_words: 200`, plus context inserted at the `after-intro` point that no other layer claims | The "Platform team convention" blockquote after the intro |
| `project` | `audience: an on-call engineer at 3am`, a per-skill `max_words`, and a forced takeover of the `rules` block | The explainer is addressed to the on-call engineer; the rules end with the project's rule and not the org's |

The rendered `max_words` is `120`: the project's skill-scoped param beats the team's shared
param, which beat the org's.

## The part worth understanding

The org and the project both patch the `rules` block. That is an error by default, and
the project resolves it with `force: true`.

Forcing **replaces** the earlier layer's patches on that target rather than stacking on top of
them, which is why the org's customer-data rule is absent from the output. If the project wanted to
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
