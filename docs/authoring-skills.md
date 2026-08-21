# Authoring a base skill

Concepts first: [concepts.md](concepts.md). This page is the mechanics.

A skill lives in `skills/<name>/`, where `<name>` is lower-kebab-case and must equal the `name`
in the frontmatter.

## Frontmatter

```yaml
---
name: code-simplification
description: Simplifies code for clarity. Use when refactoring code for clarity without changing behavior.
metadata:
  skillforge:
    version: 1.0.0
    globs:
      - "**/*"
    attribution: >-
      Adapted from addyosmani/agent-skills (MIT), skills/code-simplification at df1edb2e0548.
    params:
      test_command:
        type: string
        description: Command that runs the project's test suite.
        default: the project's test suite
      languages:
        type: list
        items: [typescript, python, react]
        description: Which language-specific sections to keep.
        default: [typescript, python, react]
---
```

| Field | Required | Meaning |
| --- | --- | --- |
| `name` | yes | Lower-kebab-case, matches the directory, at most 64 characters |
| `description` | yes | At most 1024 characters. Say **what it does and when to use it**; this text is all an agent sees when deciding whether to load the skill |
| `metadata.skillforge.version` | yes | Semver for this skill alone. Bump major when you rename or remove an anchor or param |
| `metadata.skillforge.globs` | no | File patterns this skill applies to. Consumed by the Copilot and Cursor adapters |
| `metadata.skillforge.attribution` | no | Preserved into rendered output. Required by licence when adapting someone else's work |
| `metadata.skillforge.params` | no | The param schema, below |

Any other frontmatter key (`allowed-tools`, `license`, …) is passed through untouched.

## Params

```yaml
params:
  <name>:
    type: string | bool | int | list | enum
    description: One line. Shown in errors when the param is missing.
    default: <value>          # omit to make the param required
    values: [...]             # enum only, required
    items: [...]              # list only, restricts the members
```

A param with no `default` is required: a consumer that does not supply it gets a build error
naming the param and its description.

Read a param in the body with `{{ params.name }}`. Lists render comma-separated, bools as
`true`/`false`.

Placeholders that do not look like param references pass through verbatim, so a skill can
contain `{{ sortBy: 'date' }}` in a code example without escaping. A placeholder that *does*
look like a param reference but is malformed (`{{ params.a.b }}`, `{{ param.x }}`) is an error,
because it is a typo rather than content.

## Anchors

```markdown
<!-- skillforge:point id=after-overview -->

<!-- skillforge:block id=lang-python when='"python" in params.languages' -->
### Python
...
<!-- /skillforge:block -->
```

Rules:

- Ids are unique across blocks and points in one skill.
- Blocks do not nest.
- A marker alone on its line is removed with its line, so no blank scar is left behind.

### `when` expressions

The whole language:

```
params.flag                      truthiness
not params.flag
params.framework == "react"      equality, either side
params.framework != "react"
"python" in params.languages     membership in a list or string
a and b     a or b     (a)
```

No arithmetic, no function calls, no attribute access outside `params`. Expressions are parsed,
never `eval`'d. Referencing an undeclared param is a lint error.

Use `when` for variants the skill author already knows about (a language section, a layer of the
stack). Use anchors without `when` for passages a consumer might want to rewrite. Anything else
is the skill's substance and should not be an anchor at all.

## What lint enforces

`make lint` (see [local-ci.md](local-ci.md)) fails the build on:

- a `name` that is not kebab-case or does not match the directory
- a missing or non-semver `version`
- a body or `when` referencing an undeclared param
- a relative markdown link whose target does not exist in the skill directory
- an over-long name or description

and warns about:

- a description that never says when to use the skill
- a param declared but never used
- a body over ~500 lines, which is a sign detail should move into a bundled reference file

## Bundled files

Anything else in the skill directory ships with it. `.md` and `.txt` files get param
substitution; other files are copied byte for byte. Link to them from `SKILL.md` with a relative
path so lint can verify the link.

## Changing a skill that people already import

Anchor ids and param names are public API.

| Change | Version bump |
| --- | --- |
| Editing prose inside a block | patch |
| Adding a block, point or optional param | minor |
| Renaming or removing a block, point or param; making a param required | major |
