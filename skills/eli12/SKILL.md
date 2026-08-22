---
name: eli12
description: Explain a topic like I'm a 12 year old. Use when the user types /sf-eli12 <topic> or asks for an explainer that uses real words but assumes no background, with pictures that show cause and effect.
metadata:
  skillforge:
    version: 1.0.0
    params:
      audience:
        type: string
        description: Who the explanation is for. Sets the level of every word and picture.
        default: a curious 12 year old
      medium:
        type: enum
        description: What the explainer is delivered as.
        values: [html-artifact, markdown]
        default: html-artifact
      max_words:
        type: int
        description: Hard ceiling on the word count of the whole explainer.
        default: 1000
---

# eli12

Explain like I'm {{ params.audience }}: smart, no background in this topic, and bored by being
talked down to. Pictures that show how one thing causes the next, and words that say why.

Topic: $ARGUMENTS

<!-- skillforge:point id=after-intro -->

## Rules

<!-- skillforge:block id=rules -->
- Use the real name for things, then say what it means in one plain sentence. Never replace a real term with a cute one.
- Every picture shows a cause and its effect. Arrows mean "this makes that happen".
- No more than {{ params.max_words }} words in total, captions included.
- Say what goes wrong when the thing is missing or broken. That is how {{ params.audience }} learns why it exists.
- End with one thing the reader can try or check themselves.
<!-- /skillforge:block -->

<!-- skillforge:block id=artifact when='params.medium == "html-artifact"' -->
## The artifact

Deliver a single self-contained HTML file. Inline every style and draw the pictures as inline
SVG, so the file opens anywhere with no network. Each picture gets a caption and a short "why"
paragraph beneath it, one per screen.
<!-- /skillforge:block -->

<!-- skillforge:block id=markdown when='params.medium == "markdown"' -->
## The markdown

Deliver plain markdown. Use mermaid for the pictures. Keep the caption and "why" paragraph
beneath each one.
<!-- /skillforge:block -->
