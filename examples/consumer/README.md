# Example consumer repository

A repository that owns no skills. It imports them, configures them for its own readers, and
commits the result.

Read [`skillforge.yaml`](skillforge.yaml) first; it is commented and is the whole point of the
example. Everything else in this directory is generated.

## What it demonstrates

| Thing | Where |
| --- | --- |
| Importing over git, pinned by commit | `sources:` and [`skillforge.lock`](skillforge.lock) |
| Repo-wide params, overridden per skill | `params:` at both levels |
| A `when` block disappearing | no "The artifact" section in the rendered `eli5`, because `medium` is `markdown` |
| Extending through an anchor | the `after-intro` insert and the `rules` append |
| Patching a library that never heard of skillforge | the `upstream/eli5` entry, targeted by heading path with a pinned hash |
| Four harnesses from one source | `.claude/skills/`, `AGENTS.md`, `.github/instructions/`, `.cursor/rules/` |

The same skill is imported twice on purpose: once from this library, where it carries anchors
and params, and once from its upstream, where it carries neither. Comparing the two rendered
files shows what the contract buys you.

## Rebuilding

```bash
skillforge build --root examples/consumer
```

This reaches the network and needs SSH access to the (currently private) library repository, so
it is not part of `make ci`. The committed output is what a fresh clone gets either way.

For a repository composed from three `extends` layers, see [`../layers/`](../layers/).

To see the hash-pinning work, change the `upstream_hash` on the heading patch to anything else
and rebuild. The build fails and prints the hash it actually found.
