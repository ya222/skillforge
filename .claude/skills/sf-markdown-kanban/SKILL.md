---
name: sf-markdown-kanban
description: Create, inspect, and update project todo boards that use the Markdown Kanban heading and task-property format. Use when a project tracks work in TODO.md, *.todo.md, or *.kanban.md files; when moving tasks between status columns; when adding task metadata or checklist steps; or when a repository may contain multiple independent Markdown todo boards.
metadata:
  skillforge:
    version: 1.0.2
    source: ./skills/markdown-kanban
    attribution: Adapted from holooooo/markdown-kanban (MIT), skills/markdown-kanban at 6247e4b7acb2.
---

# Markdown kanban

Manage project work as Markdown without assuming that a repository has only one todo board.

## Find the board

1. Search before editing:

   ```bash
   rg --files -g '*.todo.md' -g '*.kanban.md' -g 'TODO.md' -g 'todo.md'
   ```

2. Select the board that matches the requested workstream. Read the full file before changing it.
3. If several boards could apply and repository context does not resolve the choice, ask which board to use.
4. Create a separate `<workstream>.todo.md` when the work is independent from existing boards. Do not merge unrelated workstreams into one board merely because a todo file already exists.

## Use the format

Use one level-1 heading for the board, level-2 headings for status columns, and level-3 headings
for tasks. Column names are free-form: name them for the workflow the board tracks rather than
copying the example. A column whose heading ends in `[Archived]` is treated as archived.

````markdown
# Product delivery

## Todo

### Add export command

  - due: 2026-08-15
  - tags: [cli, export]
  - priority: high
  - workload: Hard
  - defaultExpanded: true
  - steps:
      - [x] Define the interface
      - [ ] Implement the command
      - [ ] Add tests
    ```md
    Export the current board as JSON while preserving task order.
    ```

## In Progress

## Blocked

## Done
````

Use only these task properties:

- `due`: ISO date in `YYYY-MM-DD` form.
- `tags`: comma-separated values inside brackets.
- `priority`: `low`, `medium`, or `high`.
- `workload`: `Easy`, `Normal`, `Hard`, or `Extreme`.
- `defaultExpanded`: `true` or `false`.
- `steps`: indented Markdown checkboxes.

Indent fenced descriptions by four spaces as shown. Omit empty properties instead of writing placeholders.

Keep prose out of the region between the board title and the first column heading. A Markdown
Kanban editor rewriting the board drops whatever sits there, so notes and links survive only
inside a task description.

## Update tasks

- Preserve the board title, column order, task order, and existing wording unless the request requires a change.
- Treat a task as one atomic block: its heading, properties, steps, and description move together.
- Move the complete block under the destination level-2 heading when status changes.
- Mark a step complete by changing `[ ]` to `[x]`. Do not infer completion without evidence from the work.
- Search for an existing semantic match before adding a task. Update the existing task instead of creating a duplicate.
- Keep implementation details in the description or steps. Keep the task title short and action-oriented.
- Preserve unknown Markdown outside task blocks. Do not rewrite the entire file when a focused edit is sufficient.

## Finish with a readback

Re-read the edited board and verify:

- Each task belongs to exactly one status column.
- Property values use the supported spelling and case.
- Step indentation remains nested under `steps`.
- Fenced descriptions open and close correctly.
- The requested board changed and other todo boards did not.
