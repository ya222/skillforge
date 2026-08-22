---
name: sf-eli5
description: Explain a topic like I'm a 5 year old. Use when the user types /sf-eli5 <topic> or asks for a dead-simple picture explainer of how something works.
metadata:
  skillforge:
    version: 1.0.0
    source: lib/eli5
    attribution: Adapted from anthropics/claude-plugins-community (Apache-2.0), eli5/skills/eli5 at f4c9452f5ca0.
---

# eli5

Explain like I'm an on-call engineer at 3am: someone who knows nothing about this topic. Big
pictures, few words.

Topic: $ARGUMENTS

> Platform team convention: every explainer links the dashboard that
> shows the thing it explains.

## Rules

- One idea per picture. If a picture needs a paragraph, it is two pictures.
- No more than 120 words in total, captions included.
- Every word an on-call engineer at 3am would not already know gets an everyday analogy, not a definition.
- End with the one sentence the reader should be able to repeat afterwards.
- Lead with what to do, then why; the why can wait until the pager is quiet

## The artifact

Deliver a single self-contained HTML file. Inline every style and draw the pictures as inline
SVG, so the file opens anywhere with no network. Each picture fills the viewport width with its
caption underneath, one per screen.

