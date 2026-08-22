---
name: grill-me
description: Interviews the user relentlessly about a plan, decision, or idea until nothing is left silently assumed. Use when the user types /sf-grill-me, asks to be grilled, or wants a plan or design stress-tested before any work starts.
disable-model-invocation: true
metadata:
  skillforge:
    version: 1.0.0
    attribution: >-
      Adapted from mattpocock/skills (MIT), skills/productivity/grilling at 5b15a47f2d71.
---

# Grill me

Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.

Format a round like so:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

