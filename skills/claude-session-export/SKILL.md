---
name: claude-session-export
description: Exports a Claude Code session's full conversation to a Markdown file with a bundled script, so the transcript never enters context. Use when the user asks to export, save, archive or share this session or another Claude Code session (by ID or by description) as Markdown, or to write a session transcript into a folder or notes vault.
metadata:
  skillforge:
    version: 1.0.0
---

# Claude session export

[scripts/export_session.py](scripts/export_session.py) turns a session's JSONL transcript into
one Markdown file and prints only the file's path and some counts. Run it with `python3` at its
full path under this skill's base directory. Don't read the transcript or the exported file
yourself: either would load the whole session into context, which is what the script avoids.

<!-- skillforge:point id=after-intro -->

## Pick the session

- This session: `$CLAUDE_CODE_SESSION_ID`.
- Another one: `export_session.py --list 20` prints the most recently active sessions, one per
  line: ID, last activity, project folder, title. Match the user's description against it, and
  ask when more than one fits.

## Export

```bash
python3 <skill-dir>/scripts/export_session.py <session-id> <folder or file.md>
```

- Given a folder, the script names the file `<start date> <session title>.md`. Given a path
  ending in `.md`, it writes exactly that. The folder must already exist.
- It refuses to overwrite. Re-exporting a session to update its file needs `--force`; ask first
  unless this session wrote that file.
- Each tool result is cut to 2,000 characters. Pass `--max-result-chars 0` to keep them whole
  only when the user asks for complete output.

Report the path and counts the script printed.

## What the file contains

- Frontmatter: title, session ID, the claude.ai URL when the session has one, a
  `claude --resume` command, project folder, branch, model, start, end and export times, and the
  tag `claude-session`.
- A `## User · <time>` or `## Claude · <time>` heading per turn.
- Thinking, tool calls with their results, and command output in folded Obsidian callouts, which
  collapse in Obsidian and read as quotes elsewhere.
- A marker where the context was compacted, with the summary folded.
