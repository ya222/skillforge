# Example consumer repository

A repository that owns no skills. It imports them, configures them for its own stack, and
commits the result.

Read [`skillforge.yaml`](skillforge.yaml) first; it is commented and is the whole point of the
example. Everything else in this directory is generated.

## What it demonstrates

| Thing | Where |
| --- | --- |
| Importing over git, pinned by commit | `sources:` and [`skillforge.lock`](skillforge.lock) |
| Repo-wide params, overridden per skill | `params:` at both levels |
| A `when` block disappearing | no `### Python` section in the rendered `code-simplification`, because `languages` excludes it |
| Extending through an anchor | the `after-overview` insert and the `verification` append |
| Removing a passage | `loading-and-transitions` in `frontend-ui-engineering` |
| Patching a library that never heard of skillforge | the `addy/performance-optimization` entry, targeted by heading path with a pinned hash |
| Four harnesses from one source | `.claude/skills/`, `AGENTS.md`, `.github/instructions/`, `.cursor/rules/` |

## Rebuilding

```bash
skillforge build --root examples/consumer
```

This reaches the network and needs SSH access to the (currently private) library repository, so
it is not part of `make ci`. The committed output is what a fresh clone gets either way.

To see the hash-pinning work, change the `upstream_hash` on the heading patch to anything else
and rebuild. The build fails and prints the hash it actually found.
