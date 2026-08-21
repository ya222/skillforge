# Decisions

Why the design is the way it is. Each entry is fixed unless a later entry supersedes it.
Mechanics live in [docs/](docs/); this file holds only rationale.

## 1. The runtime artifact is a plain Agent Skills directory

Everything clever happens at build time. What lands on disk is an ordinary `SKILL.md` and its
bundled files, which any harness can read and any human can debug without knowing skillforge
exists.

Rejected: a runtime resolver that harnesses call into. It would make skillforge a dependency of
every agent session rather than of the build.

## 2. Composition, not templating

The configuration layer is Kustomize-shaped: a plain base, plus overlays that declare
operations. It is not a template engine.

Rejected: Jinja or Handlebars inside `SKILL.md`. Full templating makes the base unreadable as a
skill, invites logic in prose, and has no natural stopping point.

## 3. Params are values; anchors are structure

A hard split. `{{ params.x }}` substitutes a value and can do nothing else. Adding, replacing or
removing passages is always an anchor or a patch. Keeping these apart is what stops decision 2
from eroding.

## 4. Anchors are the contract; heading paths are the escape hatch

A base author declares which passages are extensible. That contract is stable and versioned.

But a consumer's needs cannot all be anticipated, especially against a library they do not
control, so heading-path targeting exists too. It is deliberately less pleasant to use: it must
pin the target section's content hash, so upstream edits fail the build loudly rather than
patching the wrong place. Fragility that announces itself is acceptable; fragility that hides is
not.

Rejected: anchors only (every unanticipated need becomes an upstream PR or a fork) and heading
paths only (silent breakage on every upstream rename).

## 5. Rendered output is committed and drift-checked

Cloning a consumer repo yields working skills with no toolchain and no build step. Changes to a
skill show up as a reviewable diff. A digest of every generated file lives in the lockfile, so
hand-editing generated output fails `skillforge check` instead of being silently overwritten
later.

Rejected: gitignoring the output. It makes every agent session depend on having run a build
first, which is exactly the failure mode agents handle worst.

## 6. Python, distributed with uv

`uvx --from git+…` runs the tool with no registry, no publish step and no build artifacts to
host. That matters because of decision 12: releasing binaries without a hosted runner means
building them by hand.

Rejected: a Go binary (release artifacts need CI), TypeScript on npm (publishing from a laptop),
and vendored shell scripts (no way to version the tool itself).

## 7. One repository for the tool and the library

`src/skillforge/` and `skills/` with a hard boundary between them. The repo builds its own
skills with its own tool, so an awkward tool is felt here first. Splitting later is cheap;
running two repos from day one is not.

## 8. skillforge config lives under `metadata.skillforge`

The Agent Skills format reserves `metadata` for arbitrary data, so a base skill with params and
anchors is still a spec-valid skill that other tools can read. Everything about a skill stays in
one file, and the build strips the block so rendered output carries only provenance.

Rejected: a sidecar `skill.yaml` (two files to keep in sync) and top-level custom keys (breaks
strict validators elsewhere).

## 9. Conflicting layers error until the later one forces

When an org layer and a project layer patch the same anchor, the build fails and names both.
The project wins by writing `force: true`, which leaves a record in the config that the override
was deliberate. Two patches from the *same* layer both apply, because that is one author
expressing one intent.

Rejected: last-writer-wins, which makes an accidental override indistinguishable from a
considered one.

## 10. Adapters copy; they never symlink

Symlinks break on Windows, survive git badly, and cannot be drift-checked. Copies are boring and
verifiable.

## 11. A skill is the atomic unit

You import a skill, configure it and patch it. You do not compose a new skill out of fragments
of others. Name collisions across sources are an error resolved by an explicit `as:`, never by
auto-prefixing.

## 12. No hosted CI

All checks run locally, wired to git hooks. Practicalities and the accepted tradeoff are in
[docs/local-ci.md](docs/local-ci.md).

## 13. Seed skills are vendored, and one example imports live

The three shipped skills are adapted from
[addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) (MIT) with anchors and
params added; attribution travels into rendered output. Separately, `examples/consumer/` imports
that repository directly and patches it by hash-pinned heading path, which exercises the hardest
path against a library nobody here controls.

## 14. Errors, never fallbacks

Missing anchors, unknown params, drifted upstream sections, absent refs and conflicting layers
all stop the build with a message naming the file, the skill and the target. Nothing degrades
quietly. A silently skipped patch is worse than a failed build, because the skill still looks
right.

## 15. `file:` is a destination, `source:` is an origin

Discovered while writing the first `add-file` test: one key cannot mean both "the file to
create" and "the file to read content from". `file:` names the destination for `add-file` and
`remove-file`; `source:` reads patch content from a path for any op.

## 16. Only param-shaped placeholders are validated

Skill bodies legitimately contain `{{ … }}` in code examples. A placeholder that starts with
`param` or `params` must be a well-formed `{{ params.<name> }}`; anything else passes through
verbatim. This keeps typo detection where it matters without fighting real content.
