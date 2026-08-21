# Local CI

This project spends zero hosted CI minutes. Everything that would run on a runner runs on the
machine making the change, enforced by git hooks.

## Setup

```bash
make setup    # virtualenv, skillforge installed editable, pytest and ruff
make hooks    # pre-commit and pre-push hooks that run `make ci`
```

## Targets

| Target | Does |
| --- | --- |
| `make setup` | Create `.venv` and install everything |
| `make fmt` | Format and autofix |
| `make lint` | `ruff format --check`, `ruff check`, and `skillforge lint --strict` |
| `make test` | The pytest suite |
| `make build` | Re-render this repo's own skills |
| `make check` | Fail if the committed rendered output is stale |
| `make ci` | `lint`, `test`, `check`. The gate for every commit |
| `make hooks` | Install the git hooks |
| `make clean` | Remove the virtualenv and caches |

## The hooks

`make hooks` writes `pre-commit` and `pre-push` in `.git/hooks`, both running `make ci` (or
`skillforge ci` in a repo with no Makefile, which is what a consumer repo gets). Delete the
files to opt out; they are not tracked and each clone installs its own.

To bypass once, `git commit --no-verify`. If you do, the next person's `make ci` fails on your
change instead, which is the intended pressure.

## Why no GitHub Actions

Deliberate. See [DECISIONS.md](../DECISIONS.md), decision 12.

The tradeoff is real: nothing verifies a push from a machine with hooks uninstalled. The
mitigations are that `make ci` is fast (about a second), that committed output makes staleness
visible in review as a missing diff, and that `skillforge check` reproduces the whole build from
the lockfile, so anyone can verify a commit locally.

## Testing philosophy

Tests build real repositories in temporary directories and run the real pipeline: real files,
real git repositories over `file://` for source fetching, real rendered output. There are no
mocks. The only unit-level tests are for the `when` expression parser, where the input space is
small and enumerable.

`tests/test_seed_skills.py` renders the actual skills this repo ships under several
configurations, so a change to a skill that breaks its anchors fails the suite.
