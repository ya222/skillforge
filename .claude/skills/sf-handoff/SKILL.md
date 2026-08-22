---
name: sf-handoff
description: Compacts the current conversation into a handoff document that a fresh agent can pick up from. Use when the user types /sf-handoff, is running out of context, is about to stop for the day, or wants to move the work to a new session.
argument-hint: What will the next session be used for?
disable-model-invocation: true
metadata:
  skillforge:
    version: 1.0.0
    source: ./skills/handoff
    attribution: Adapted from mattpocock/skills (MIT), skills/productivity/handoff at 5b15a47f2d71.
---

# Handoff

Write a handoff document so a fresh agent, with none of this conversation, can continue the work.
Save it to the OS temporary directory, not the workspace, and print its path as the last line of
your reply.

If the user passed arguments, they describe what the next session will focus on. Tailor the
document to that, and say what it leaves out.

## What goes in

In this order:

1. **Goal.** What the user is trying to achieve, in their words where you have them.
2. **State.** What is done, what is in progress, what is untested. Be precise about whether
   something was verified or only written.
3. **Decisions.** Choices made and why, especially ones the user corrected you on. The next
   agent must not relitigate them.
4. **Next steps.** Concrete, in order, starting with the one to do first.
5. **Where things are.** Files, branches, commits, URLs, commands that matter. Reference
   specs, plans, ADRs, issues, diffs and commits by path or URL; never paste their content.
6. **Suggested skills.** Which skills the next agent should load with the Skill tool, and for
   what.

## Rules

- Redact API keys, passwords, tokens and personal data. The file lands outside the repo.
- Don't duplicate what other artifacts already hold. Point at them.
- Write for someone who will read only this document. Short, declarative, no narrative of the
  conversation.
