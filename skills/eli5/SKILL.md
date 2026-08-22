---
name: eli5
description: Explain a topic like I'm a 5 year old. Use when the user types /sf-eli5 <topic> or asks for a dead-simple picture explainer of how something works.
metadata:
  skillforge:
    version: 1.0.0
    attribution: >-
      Adapted from anthropics/claude-plugins-community (Apache-2.0), eli5/skills/eli5
      at f4c9452f5ca0.
    params:
      audience:
        type: string
        description: Who the explanation is for. Sets the level of every word and picture.
        default: a 5 year old
      medium:
        type: enum
        description: What the explainer is delivered as.
        values: [html-artifact, markdown]
        default: html-artifact
      max_words:
        type: int
        description: Hard ceiling on the word count of the whole explainer.
        default: 300
---

# eli5

Explain like I'm {{ params.audience }}: someone who knows nothing about this topic. Big
pictures, few words.

Topic: $ARGUMENTS

<!-- skillforge:point id=after-intro -->

## Rules

<!-- skillforge:block id=rules -->
- One idea per picture. If a picture needs a paragraph, it is two pictures.
- No more than {{ params.max_words }} words in total, captions included.
- Every word {{ params.audience }} would not already know gets an everyday analogy, not a definition.
- End with the one sentence the reader should be able to repeat afterwards.
<!-- /skillforge:block -->

<!-- skillforge:block id=artifact when='params.medium == "html-artifact"' -->
## The artifact

Deliver a single self-contained HTML file. Inline every style and draw the pictures as inline
SVG, so the file opens anywhere with no network. Each picture fills the viewport width with its
caption underneath, one per screen.
<!-- /skillforge:block -->

<!-- skillforge:block id=markdown when='params.medium == "markdown"' -->
## The markdown

Deliver plain markdown. Use mermaid for the pictures.
<!-- /skillforge:block -->
