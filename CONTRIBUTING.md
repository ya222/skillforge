# Contributing

## Before you change anything

```bash
make setup
make hooks
```

`make hooks` installs pre-commit and pre-push hooks that run `make ci`. This project has no
hosted CI, so those hooks are the only gate. See [docs/local-ci.md](docs/local-ci.md).

## Changing a skill

Read [docs/authoring-skills.md](docs/authoring-skills.md). Bump the skill's version according to
the table at the end of it, then `make build` and commit the regenerated output alongside your
change.

## Changing the tool

Read [AGENTS.md](AGENTS.md) for the repository map and the invariants, and
[DECISIONS.md](DECISIONS.md) before proposing anything that contradicts a decision there. If a
decision turns out to be wrong, change it in that file in the same pull request.

Tests build real repositories and run the real pipeline. Add to the existing integration-style
suites rather than mocking.

## Committing

`make ci` must pass. Rendered output under `.agents/`, `.claude/` and the managed region in
`AGENTS.md` is generated: never hand-edit it, and always commit it with the change that caused
it.
