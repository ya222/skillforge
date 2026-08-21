# CLI reference

Run without installing:

```bash
uvx --from git+https://github.com/ya222/skillforge skillforge <command>
```

Or install into a project: `uv pip install git+https://github.com/ya222/skillforge`.

Every command takes `--root` to point at a repository other than the current directory. Every
failure exits non-zero with a message naming the file, the skill and the target involved.

| Command | Does |
| --- | --- |
| `init` | Writes a starter `skillforge.yaml`. Fails if one exists |
| `add <ref> [--as NAME]` | Appends a skill entry to `skillforge.yaml` |
| `build` | Renders every configured skill, writes the outputs, rewrites `skillforge.lock` |
| `check` | Fails if committed output or the lockfile is stale. Changes nothing |
| `lint [--skills DIR] [--strict]` | Validates the base skills this repo authors. `--strict` fails on warnings |
| `update [ALIAS…]` | Re-resolves sources to the tip of their refs and rebuilds. With no argument, updates all of them |
| `eject <NAME>` | Copies an imported skill into `skills/` and repoints the config at the copy |
| `ci` | `lint` then `check`. What the git hooks run in a consumer repo |
| `install-hooks` | Installs pre-commit and pre-push hooks |

Notes:

- `build` and `update` are the only commands that write generated files.
- `add` and `eject` rewrite `skillforge.yaml` through a YAML round-trip, which normalises
  comments and formatting. Hand-editing the file is equally valid and preserves them.
- `eject` drops the skill's patches, because they are now part of the copied text. It says so
  when it runs.
- `update` prints each source's old and new commit, so a review shows exactly what moved.
- In this repository, use `make` instead: see [local-ci.md](local-ci.md).
