---
name: sf-deepseek-paraphrase
description: Rewrites text in fresh wording with DeepSeek through a bundled script, keeping its meaning and structure. Use when the user types /sf-deepseek-paraphrase, or asks to paraphrase or reword a draft, a file or Claude's own output with DeepSeek.
metadata:
  skillforge:
    version: 1.0.0
    source: ./skills/deepseek-paraphrase
---

# DeepSeek paraphrase

[scripts/paraphrase.py](scripts/paraphrase.py) sends a file to the DeepSeek API, asks for a
full rewrite that keeps the meaning and structure, writes the result to a new file, and prints
only the path and counts. Run it with `python3` at its full path under this skill's base
directory. It needs `DEEPSEEK_PARAPHRASE_API_KEY` in the environment; if it is missing, say so
and stop.

## Run it

1. Write the text to a file. When the text is your own output in this session, write it
   straight to the file instead of printing it first.
2. Run:

   ```bash
   python3 <skill-dir>/scripts/paraphrase.py <in-file> <out-file>
   ```

   - It refuses to overwrite `<out-file>`; pass `--force` only when the user asks.
   - `--model` picks another DeepSeek model. `--temperature` defaults to 1.0; higher means
     more varied wording.
   - If it reports that DeepSeek stopped early, split the input at a heading or paragraph
     break and run each part.
3. Report the path and counts the script printed. Read the output file only when the user
   wants to see it or check it.

## Check the result

When the user wants it checked, compare the two files for facts, numbers, names, code and
links. The rewrite should change those not at all. Fix any drift by hand in the output file
and say what you changed.
