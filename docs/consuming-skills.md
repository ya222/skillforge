# Consuming skills

Concepts first: [concepts.md](concepts.md). This page is the `skillforge.yaml` reference.

A JSON Schema for editor completion lives at [`schema/skillforge.schema.json`](../schema/skillforge.schema.json).

## The file

```yaml
version: 1

extends:
  - org                      # a source alias, or a path like ../shared

sources:
  lib:      { git: https://github.com/ya222/skillforge, ref: v0.1.0 }
  upstream: { git: https://github.com/anthropics/claude-plugins-community, ref: main, path: eli5/skills }

params:
  audience: a new hire
  max_words: 300

skills:
  - from: lib/eli5
    as: explain                        # optional rename
    params:
      medium: markdown
    patches:
      - { block: rules, op: append, content: "- Link the runbook at the end" }

  - from: ./skills/house-style          # a skill this repo owns

targets:
  claude-code: {}
  agents-md: { path: AGENTS.md }
  copilot: {}
  cursor: {}

output: .agents/skills
```

| Key | Meaning |
| --- | --- |
| `version` | Config format version. Currently always `1` |
| `extends` | Parent configs, applied in listed order before this file |
| `sources` | Git repositories to import from. `ref` is a branch, tag or SHA; `path` is where skills live in that repo, default `skills` |
| `params` | Repo-wide param values |
| `skills` | What to render |
| `targets` | Which harnesses to emit for. See [adapters.md](adapters.md) |
| `output` | Canonical rendered directory, default `.agents/skills` |

`from:` is either `<source-alias>/<skill-name>` or a path starting with `.` or `/`, resolved
relative to the config file that declared it. Two skills rendering to the same name is an error;
rename one with `as:`.

## Patches

Every patch is one `op` against one target.

| Target | Key | Notes |
| --- | --- | --- |
| Block anchor | `block: <id>` | Supports `replace`, `append`, `prepend`, `remove` |
| Point anchor | `point: <id>` | Supports `insert` only |
| Heading path | `heading: A > B` | Any op except `insert`. Requires `upstream_hash` |
| Frontmatter | `key: <dotted.path>` | With `op: set-frontmatter` |
| Bundled file | `file: <path>` | With `op: add-file` or `remove-file` |

| Op | Effect |
| --- | --- |
| `replace` | Replaces the block's contents, or a heading section's body below its heading line |
| `append` / `prepend` | Adds at the end or start of the target |
| `insert` | Inserts at a point |
| `remove` | Removes the whole block, or a heading section including its heading |
| `add-file` / `remove-file` | Adds or removes a bundled file. `file:` is the destination path |
| `set-frontmatter` | Sets `key:` in the rendered frontmatter to `content:` |

Content comes from `content:` (inline) or `source:` (a path relative to the config that declared
the patch). Patch content is param-substituted like any other body text.

Targeting a block or point that the skill does not declare is an error listing the ones it does.
Two patches whose spans overlap is an error, and so is inserting at a point inside a region another patch removes or rewrites, since the inserted content would be discarded. See [concepts.md](concepts.md) for the `force: true`
rule when two layers collide.

### Heading patches

```yaml
- heading: "eli5"
  op: append
  content: "Always end with the one sentence the reader should remember."
  upstream_hash: sha256:9f2a…
```

To find the hash, write the patch without it and run `skillforge build`. The error names the
current hash; paste it in after reading the section and confirming the patch still makes sense.
When upstream later edits that section, you get the same error again, which is the point.

## The lockfile

`skillforge.lock` is generated and must be committed. It records:

- the exact commit each source resolved to, so builds are reproducible and offline
- each skill's version and a hash of its base, so you can see what actually changed upstream
- a digest of every generated file, so `skillforge check` detects hand edits to generated output

Never edit it by hand.

## Day-to-day

```bash
skillforge build      # render and write
skillforge check      # fail if committed output is stale (this is what CI runs)
skillforge update     # move sources to the tip of their refs, then rebuild
skillforge eject NAME # take a skill local and cut the upstream link
```

Full command reference: [cli.md](cli.md).

Generated files are not for hand editing. `check` will catch it, and the next `build` would
overwrite it. Put the change in `skillforge.yaml` as a patch instead.
