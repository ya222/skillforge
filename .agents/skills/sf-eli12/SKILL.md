---
name: sf-eli12
description: Explain a topic like I'm a 12 year old. Use when the user types /sf-eli12 <topic> or asks for an explainer that uses real words but assumes no background, with pictures that show cause and effect.
metadata:
  skillforge:
    version: 1.0.0
    source: ./skills/eli12
---

# eli12

Explain like I'm a curious 12 year old: smart, no background in this topic, and bored by being
talked down to. Pictures that show how one thing causes the next, and words that say why.

Topic: $ARGUMENTS

## Rules

- Use the real name for things, then say what it means in one plain sentence. Never replace a real term with a cute one.
- Every picture shows a cause and its effect. Arrows mean "this makes that happen".
- No more than 1000 words in total, captions included.
- Say what goes wrong when the thing is missing or broken. That is how a curious 12 year old learns why it exists.
- End with one thing the reader can try or check themselves.

## The markdown

Deliver plain markdown. Use mermaid for the pictures. Keep the caption and "why" paragraph
beneath each one.
