---
name: sf-dev-style
description: Writes and edits developer documentation in the Google developer documentation style. Use when writing or reviewing READMEs, guides, tutorials, API references, UI procedures, release notes, error messages, or any prose aimed at developers, and when asked to make docs clearer, more consistent, or more accessible.
metadata:
  skillforge:
    version: 1.0.0
    source: ./skills/dev-style
    attribution: Condensed from the Google developer documentation style guide, https://developers.google.com/style, Creative Commons Attribution 4.0.
---

# Google developer documentation style

Write like a knowledgeable friend who understands what the developer wants to do: conversational,
direct, and respectful, never frivolous or pedantic. Clarity for a global audience comes before
everything else. Where a rule here is silent, follow the guide at
https://developers.google.com/style and its word list at
https://developers.google.com/style/word-list.

## Voice and tone

- Second person. "You", not "we" or "the user", for the reader. "We" only for the team that
  made the product, and rarely.
- Active voice. Say who does what. "The server returns an error", not "an error is returned".
- Present tense. "The command creates a file", not "will create".
- Conditions before instructions. "If the build fails, check the log", not "Check the log if
  the build fails."
- Standard American spelling and punctuation.
- No exclamation marks. No "please" in instructions. No "let's". No "simply", "easily",
  "quickly", "just", or "obviously": if it were that easy the reader would not be here.
- No placeholder phrases such as "please note that" or "at this time". No buzzwords, slang,
  pop-culture references, metaphors, or culturally specific references.
- No "e.g." or "i.e.": write "for example" and "that is". No "etc." at the end of a list: say
  up front that the list is not exhaustive.
- Vary sentence openings. A procedure where every sentence starts with "You can" is a list.
- Sentences under 26 words. One idea per sentence, one topic per paragraph. Front-load the
  important part.
- Spell out abbreviations on first use, with the abbreviation in parentheses; skip the
  abbreviation entirely if the term appears once. AI, API, HTML, JSON, PDF, REST, URL and byte
  units need no spelling out. Never use an abbreviation as a verb ("connect by using SSH", not
  "SSH into").
- Don't document future features, timelines, or anything unreleased. Don't write "currently"
  or "new"; the doc outlives the moment.

## Word choices

| Write | Not |
| --- | --- |
| lets you | allows you to, enables you to |
| use | utilize, leverage |
| run | execute |
| select, clear (a checkbox) | check, uncheck, tick |
| click (desktop), tap (touch) | click on, hit, press (a button on screen) |
| enter (a value) | type, input |
| turn on, turn off | enable, disable (for settings a user flips) |
| earlier, later, preceding, following | above, below, right-hand |
| see | refer to, check out |
| for example, such as | e.g. |
| that is | i.e. |
| can (ability), might (possibility), must (requirement) | may (ambiguous), should (unless a recommendation) |
| app | application (for end-user software) |
| whether | if (for a choice between alternatives) |
| data is | data are |
| email | e-mail |
| allowlist, blocklist | whitelist, blacklist |
| primary/replica, controller/worker | master/slave |
| final check, quick check | sanity check |
| doesn't respond | hangs |
| person-hours, humanity | man-hours, mankind |

Use the product's own name in full ("Google Cloud console", not "the console"). Say "version 3",
never "the latest version". Describe features by what they do, not by how easy they are.

## Inclusive and accessible writing

- Avoid ableist words and figures of speech: crazy, dumb, blind to, cripples. Say what you mean:
  baffling, slows down, unaware of.
- People first: "people with disabilities", "older adults", "uses a wheelchair". Never "the
  disabled", "suffering from", "wheelchair-bound".
- Use diverse names, pronouns, and locations in examples. Use gender-neutral pronouns.
- No double negatives. "You can continue without a path", not "a missing path won't prevent
  you from continuing."
- No directional language. The reader might be listening, not looking.
- Define every image with alt text that states its purpose. Don't put text, code, or terminal
  output in images. Prefer SVG to PNG.
- Don't rely on color alone to convey meaning. Don't describe UI elements by their look; use
  their label.
- Introduce tables, interactive elements, and expandable sections in the text before them.
  Don't merge table cells. Don't put a table in the middle of a procedure.
- Write "and", not "&", except in UI labels that use it.

## Headings

- Sentence case, always. "Create an instance", not "Create An Instance".
- Task headings start with a bare imperative: "Create an instance", not "Creating an instance".
  Conceptual headings are noun phrases: "Migration to the cloud". Don't open any heading with
  an -ing word.
- One h1 per page. Don't skip levels. No empty headings, no numbers to show sequence, no links,
  no code without a descriptive noun ("The `gcloud` command", not "`gcloud`").
- Keep punctuation out of headings. A heading that needs it needs rewriting.
- Refer to grouped subsections as "the following sections".

## Lists

- Introduce every list with a complete sentence ending in a colon. "Use the button for any of
  the following purposes:", not "Use the button to:".
- Numbered for sequence. Bulleted for everything else. Description lists for term/definition
  pairs (bold run-in term, then the description).
- Capitalize each item. End with a period unless the item is a single word, has no verb, is
  entirely code, or is a link or title.
- Parallel structure: every item in one list takes the same grammatical form.
- No one-item lists. Make clear whether every item is required or any one of them.
- Serial commas in inline lists: "A, B, and C".

## Procedures

- State the goal, then the action: "To start a document, click **File > New > Document**."
- State the location before the action: "In the **Name** field, enter a name."
- One action per step. Sub-steps use lowercase letters. A single-step procedure is one
  bulleted sentence, not a numbered list.
- Put the result of a step in the same paragraph, after the action: "Click **Run**. The
  results appear in the **Output** pane."
- Mark optional steps with "Optional:" at the start of the step. Never "(Optional)".
- Put prerequisites before the first step, never in a note after it.
- For a command step, in this order: what the command does, the command, what each placeholder
  means, further explanation, the output, what the output means.
- Say what the command does, not "run the following command".
- Document the simplest accessible method. Put alternatives in separate sections, not
  interleaved.
- Link to an earlier procedure instead of repeating it.

## UI elements

- Bold every UI label, matching its on-screen capitalization except that all-caps labels become
  sentence case: **Refresh**, not **REFRESH**. Drop trailing ellipses: **Browse**, not
  **Browse...**.
- Refer to elements by label plus type on first mention: the **Settings** menu, the **Edit**
  tab, the **Owner** field, the **Terms** checkbox. Never use a label as a verb or noun: "In
  the **Name** field, enter a name", not "**Name** the account".
- Click a button by its label alone: "Click **OK**", not "click the OK button".
- Menu paths in one bold run with angle brackets: **File > Tools > Options**.
- "In" a dialog, field, list, menu, pane, window. "On" a page, tab, toolbar.
- Select or clear a checkbox. Select a radio option. Click a toggle to the on position (don't
  use "toggle" as a verb). Expand or collapse a section.
- Keys: spell out modifiers, capitalize letters, join with plus, no spaces: Control+Shift+S.
  "Press" a key combination; "enter" text. Give macOS in parentheses after Windows and Linux:
  "Press Control+C (or Command+C on macOS)."

## Code

- Code font for anything that is literally typed or literally returned: commands, flags,
  filenames, paths, method and class names, keywords, environment variables, HTTP methods and
  status codes, port numbers, IP addresses, query parameters, values the reader enters,
  literal output. Not for product names, domain names in prose, or URLs the reader visits.
- Never inflect a code element. Add a noun and inflect that: "the `ADDRESS` constant's value",
  "send a `POST` request", "call the `close` method". Never "`POST` the data".
- Code blocks: preformatted, wrapped at 80 characters, indented per the language's style guide.
  Show omitted code with a comment in the language's syntax, never with an ellipsis.
- Introduce a sample with a colon if it follows immediately, a period if anything sits between.
- Placeholders are uppercase with underscores: `PROJECT_ID`, `BUCKET_NAME`. Never `myProject`,
  `<project>`, `xxx`, or anything starting with `MY_` or `YOUR_`. In Markdown, italicize inline
  placeholders: *`PROJECT_ID`*. Explain every placeholder on first use: "Replace `PROJECT_ID`
  with the ID of your project." For several, introduce with "Replace the following:" and list
  them.
- Command-line syntax: brackets for optional arguments, an ellipsis for repeats, outside the
  placeholder.

## Links

- Link text is the destination's title or a description of it, important words first. Never
  "click here", "this document", or a raw URL.
- Introduce cross-references with "For more information, see [Title]." or "For more
  information about X, see [Title]." Use "see", not "refer to".
- Say when a link downloads a file (and its type), opens a new tab, or leaves the site. Don't
  force new tabs. Don't use an external-link icon.
- Punctuation goes outside the link. No quotation marks around linked titles.
- Link each destination once per page. Every link is a decision you're asking the reader to
  make; if a sentence of context would do instead, write the sentence.

## Notices

Four types, in rising severity: Note, Caution, Warning, and Success (only for interactive
content). Use a note only when the information is relevant, skippable, and outside the flow.
Never for prerequisites, steps, cross-references, or expected results. Never stack two
notices. Label the type in bold: **Note:**, **Caution:**, **Warning:**.

## Numbers, dates, and times

- Spell out zero through nine; numerals from 10. Exceptions always take numerals: versions,
  units and technical quantities ("6 queries per second", "128 bits"), step, page, and chapter
  numbers, prices, and any number in a sentence that also has a numeral of 10 or more.
- Spell out a number that starts a sentence. Spell out ordinals: "first", never "1st".
- Commas from four digits: 1,532. Decimals, not fractions: 0.75. Percentages with no space:
  40%. Ranges with a hyphen and no spaces: 2012-2016. Dimensions with a lowercase x: 192x192.
- Dates in full: "January 19, 2017"; with a weekday, "Tuesday, April 27, 2021". Month and year
  without a comma: "January 2017". A full date mid-sentence takes a comma after the year.
  Numeric only when unavoidable, and then ISO: 2017-04-15.
- Times on the 12-hour clock with capital AM and PM and a space: "3 PM", "3:45 PM". Drop ":00".
  Spell out time zones with the UTC offset: "Pacific Standard Time (UTC-8)". Date before time.
- Never refer to seasons; hemispheres disagree. Name the months.

## Before you finish

Read it aloud. If it sounds like nobody would say it, rewrite it. Then check that every
instruction says where, what, and why; every list is introduced and parallel; every UI label is
bold; every code item is in code font and not inflected; every link makes sense out of context;
and nothing tells the reader it's easy.
