---
name: obsidian-vault
description: Finds, reads, creates and edits notes in the user's Obsidian vault at {{ params.vault_path }}, from any project. Use when the user mentions Obsidian, their vault or their notes, or asks to look something up in, save something to, or update a note.
metadata:
  skillforge:
    version: 1.0.0
    params:
      vault_path:
        type: string
        description: Absolute path to the local Obsidian vault, the folder that contains `.obsidian/`.
---

# Obsidian vault

The user's Obsidian vault is `{{ params.vault_path }}`: plain markdown files, one note per file,
in folders the user arranged. Work on the files directly, from whatever directory this session
started in.

If that folder or its `.obsidian/` directory is missing, stop and tell the user the configured
path is wrong. Don't search the disk for another vault.

<!-- skillforge:point id=after-intro -->

## Before reading or editing

If the vault is a git repository, run `git -C "{{ params.vault_path }}" pull --ff-only` first.
Notes edited elsewhere, such as on claude.ai or a phone, reach this copy only through the
remote. If the pull fails, report it; don't merge, stash or reset.

## Finding notes

- Search `*.md` with `rg` or `grep -ri`, excluding `.obsidian/` and `.git/`. A note's title is
  its file name, so search names as well as contents.
- Cite what you found by its path relative to the vault.

## Writing notes

- Use Obsidian-flavoured markdown: `[[Note name]]` links to other notes, `![[file]]` embeds,
  YAML frontmatter for properties.
- Put a new note in the folder that fits it, and ask when none does. Attachments go in the
  folder named by `attachmentFolderPath` in `.obsidian/app.json`.
- Keep `\ / : # ^ [ ] |` and `* " < > ?` out of file names; they break the file or its links.
- Change only what was asked; don't reformat the rest of a note.
- Renaming or moving a note outside Obsidian doesn't update links to it. Update the `[[...]]`
  references across the vault in the same change.
- Don't touch anything under `.obsidian/` unless asked.

## Exporting Claude sessions

To save this Claude Code session or another one into the vault, use the claude-session-export
skill. The rules above still apply: pull first, then pick the folder the way you would for a new
note and pass that folder as the output, so the script names the file. Don't read the exported
note back. Its frontmatter holds the session's ID and URL; if the session was about notes already
in the vault, offer to add a `[[link]]` to the export in those notes.

## Syncing

If `.obsidian/plugins/obsidian-git/` exists, that plugin commits, pushes and pulls on a timer
while Obsidian is open, so leave git to it: don't commit or push from this session. Changes made
while Obsidian is closed sync the next time it opens. Without the plugin, ask the user before
committing.
