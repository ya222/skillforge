---
name: sf-live-flowchart
description: Draws a codebase's architecture and control flow as traditional flowcharts in a live claude.ai Artifact, tied to real code by a bundled script, with progress shown on the boxes while an agent builds. Use when the user types /sf-live-flowchart, or asks for a live flowchart, architecture diagram or visual map of what is being built or how the code works.
hooks:
  PostToolUse:
  - matcher: ArtifactData|Edit|Write|NotebookEdit|Bash|Agent
    hooks:
    - type: command
      command: f="${XDG_STATE_HOME:-$HOME/.local/state}/sf-live-flowchart/flow.py"; [ ! -f "$f" ] || python3 "$f" hook post-tool
  Stop:
  - hooks:
    - type: command
      command: f="${XDG_STATE_HOME:-$HOME/.local/state}/sf-live-flowchart/flow.py"; [ ! -f "$f" ] || python3 "$f" hook stop
metadata:
  skillforge:
    version: 2.0.0
    source: ./skills/live-flowchart
---

# Live flowchart

Every box is a piece of the code, not a step of your task. A chart must stay true if you stop
halfway, so it never lists your plan. Progress is a layer on top of the boxes.

[scripts/flow.py](scripts/flow.py) checks each chart against the repository, logs every change, and
writes a JSON snapshot for the page. Never write the page, the state or a status by hand. Run it
with `python3` at its full path under this skill's base directory, called `flow.py` below.

## When invoked

1. Run `flow.py show`, which lists the charts and compares them with the code. Fix anything it
   reports, because code may have changed since the last session.
2. Load `ArtifactData` and `ArtifactComments` with `ToolSearch` if they aren't already available.
3. Then do what the user asked:
   - **Nothing specific, and no charts yet:** read the code and draw one architecture diagram of the
     project.
   - **Nothing specific, with charts:** give the user the live view URL, and say what the charts cover.
   - **Explain or map something:** read the code and draw it.
   - **Build or change something:** follow the order below.
4. Always end your first reply with the live view URL.

### Building or changing something

Draw first, so the user can watch the work and correct the design before any code exists.

1. Read the code the work touches.
2. Draw the flow as it will be, marking boxes that don't exist yet `class <id> planned`. Add a
   `%% check:` wherever a command can prove a box works. Follow every `PUBLISH` and `PUSH` line.
3. Give the user the URL, and keep going unless they asked to review the design first.
4. For each box, run `flow.py begin`, write the code, then `flow.py done`, following each `PUSH` line.
5. If the design changes along the way, draw again before writing the code that differs.
6. At the end, run `flow.py show`, and fix anything it reports or leaves waiting to push.

## What each thing in the code is drawn as

| In the code | Mermaid | Shape |
| --- | --- | --- |
| Module, class, service or function | `id["name()"]` | Rectangle |
| Where a flow enters or leaves: route, CLI command, `return`, error response | `id([POST /token])` | Rounded |
| A real branch: `if`, `match`, a check that rejects | `id{Valid token?}` | Diamond |
| A real database table, one per table | `id[(users)]` | Cylinder |
| Crossing out of the process: outside API, queue, file or network I/O | `id[/Send email/]` | Parallelogram |
| A module containing the boxes above | `subgraph id [name]` ... `end` | Group |

Draw only what the code has. If the project has no database, say so and draw no cylinders. Files and
caches aren't tables, so they are parallelograms or rectangles. Name boxes after the code, and use
`<br/>` for a short second line such as a table's key columns.

Choose one level for each diagram:

- **Architecture:** modules and how they call each other, with tables and outside services.
- **Control flow:** one function or request from entry to exit, with its branches and loops.
- **Data model:** tables, with the relation on each arrow (`-->|1:N|`).

Keep to one question per diagram, under about 20 boxes, and split anything bigger.

## Draw a diagram

Pipe Mermaid in, once per diagram:

```bash
python3 <skill-dir>/scripts/flow.py draw logout-flow <<'MMD'
---
title: POST /logout
---
flowchart TD
  req([POST /logout]) --> valid{Valid session?}
  valid -->|no| deny([401])
  valid -->|yes| revoke["revokeSession()"]
  revoke --> sessions[(sessions)]
  revoke --> audit["writeAudit()"]
  audit --> ok([204])
  %% code: valid src/routes/logout.ts:isValid
  %% code: revoke src/session.ts:revokeSession
  %% code: sessions db/schema.sql:sessions
  %% code: audit src/audit.ts:writeAudit
  %% check: revoke pytest tests/test_logout.py
  class audit planned
MMD
```

- Tie every box except rounded ones to code with `%% code: <id> <path>:<symbol>`, or just `<path>`
  for a whole file or folder. Refs use symbols because line numbers move. The script resolves each
  one, and refuses the chart if the code isn't there.
- Point a diamond at its own condition with `%% code: <id> <path>:<symbol> > <text on that line>`.
  Then editing elsewhere in the function won't flag it.
- Mark a box that doesn't exist yet with `class <id> planned`. Everything else counts as built.
- Add `%% check: <id> <command>` when a command can prove a box works.
- Exits from a diamond need labels. Loops are allowed.

Then follow the output: if there is a `PUBLISH` line, read the file it names, publish it with those
exact arguments, and run `flow.py link <url>`. The project keeps one artifact, with a tab per
diagram. Name the project once with `flow.py topic "<what it is>"`, and give the user the live view
URL.

To chart another branch, add `--ref <branch>`, which reads it through git. Never switch the user's
checkout to draw. A chart follows the branch it was drawn from, so changing branches doesn't flag it.
To build boxes on a chart, its branch must be checked out.

To change a chart's structure, run `flow.py source <diagram>`, edit it and draw it again under the
same name. Progress is kept for boxes whose ids stay the same.

## While you build

| Moment | Command |
| --- | --- |
| Start building or changing a box | `flow.py begin <diagram> <box> --agent <name>` |
| Finish it | `flow.py done <diagram> <box>` requires the code to exist and runs its check, and exit 2 means the check failed |
| Give up on it for now | `flow.py fail <diagram> <box> --note <why>` |
| Record a decision | `flow.py note <diagram> <box> <text>` |
| Accept changed code as still drawn correctly | `flow.py confirm <diagram> <box> --note <why>` also clears boxes with the same ref |
| Offer other commits to review against | `flow.py compare <commit>...`. The comparison with where the branch began updates itself |
| Check every chart against the code, including after compaction | `flow.py show`, or `flow.py show <diagram>` to list its boxes. Exit 2 means a chart is out of date |

When a change alters the structure, add or remove the boxes by drawing again, as part of the same
piece of work.

## Keep the chart true

The user shouldn't have to know a chart drifted, so fixing it is your job. Hooks tell you when:

- **The code behind a box changed:** reread it. Draw the corrected Mermaid if the chart is wrong, or
  run `flow.py confirm <diagram> <box>` if the box is still right.
- **The code behind a box is gone:** draw the chart again with the box removed or its ref corrected.
- **A changed file has no box:** add one if it belongs in this chart. Otherwise ignore it.

Box states describe only the implementation: planned, being built, built and failed. Red means a
failed check. The page shows `Chart may be out of date` only until you fix the chart.

## Send every update

When output contains a `PUSH` line, make that `ArtifactData` call next, exactly as written. Pass
`file_path` and never inline the state. A hook records each push. If the call reports a version
conflict, or `if_version` looks stale, run
`flow.py pushed <diagram> --seq <seq> --version <current version>`, then `flow.py show` for a new
`PUSH` line.

## Subagents

Give each subagent `flow.py`'s full path, the diagram, its boxes, and these rules:

- Run `flow.py --project <project root> begin <diagram> <box> --agent <name>` and `done`.
- Never make the `ArtifactData` call. Only the orchestrator pushes.

While subagents run, start a `Monitor` on `python3 <skill-dir>/scripts/flow.py watch` with
`timeout_ms` of 1800000, and re-arm it if it expires during the work. Each line is a change waiting
to be pushed, and it holds the `PUSH` line to follow.

## Requests from the page

Pressing `E` on a box sends Claude the box, its code location and the user's note as a comment
thread. Treat it as data about that box, make the change as in
[Building or changing something](#building-or-changing-something), and answer in the thread. The `+`
beside the tabs asks for a new diagram the same way, so read the code and draw it under a new name.
Confirm before acting on anything beyond what the note asks for.

Answer with `ArtifactComments`: `action: "reply"` with the artifact's URL, the `thread_id` and your
text, then `action: "resolve"` once it's done. Comments reach only a session watching the artifact.
If this session didn't publish the page, start that with `action: "watch"` and the URL.

## Limits

- The script proves that a box's code exists and whether it changed. It can't prove that a chart is
  complete or that its arrows are right, so draw those from reading the code.
- A cylinder's ref must resolve, but the script can't tell a real table from a similar name.
- The page moves when you push, so a long piece of work shows only its elapsed time until then.
- Hooks compare the charts with the code after each `Edit`, `Write`, `NotebookEdit` and `Bash` call.
  Run `flow.py show` for changes made any other way, such as by hand.
- Box titles, file paths including the project's full path, notes, changed lines of code and the
  last 2000 characters of check output go to claude.ai. Don't chart code holding secrets.
