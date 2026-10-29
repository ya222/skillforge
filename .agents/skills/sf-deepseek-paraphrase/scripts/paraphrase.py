#!/usr/bin/env python3
"""Rewrite text in fresh wording with DeepSeek, keeping its meaning and structure.

Reads a file, writes the rewrite to another file, and prints only the output path and counts,
so the text never has to pass through the agent's context.

Standard library only. Needs DEEPSEEK_PARAPHRASE_API_KEY. Usage:
    paraphrase.py IN OUT [--model M] [--temperature T] [--force]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-flash"
TIMEOUT_SECONDS = 300

SYSTEM_PROMPT = """\
Rewrite the user's text in your own words. Keep every fact, claim, number, name, code span,
link and the overall structure (headings, lists, paragraphs, Markdown). Change wording and
sentence construction throughout: do not keep any phrase longer than four words from the
original except names, quotations, code and technical terms. Keep the tone and length roughly
the same. Output only the rewritten text, with no preamble or commentary."""


def paraphrase(text: str, model: str, temperature: float, api_key: str) -> tuple[str, dict]:
    body = json.dumps(
        {
            "model": model,
            "temperature": temperature,
            "thinking": {"type": "disabled"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        }
    ).encode()
    request = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as e:
        sys.exit(f"error: DeepSeek returned HTTP {e.code}: {e.read().decode(errors='replace')}")

    choice = payload["choices"][0]
    if choice["finish_reason"] != "stop":
        sys.exit(f"error: DeepSeek stopped early ({choice['finish_reason']}); split the input")
    return choice["message"]["content"], payload["usage"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--force", action="store_true", help="overwrite OUT if it exists")
    args = parser.parse_args()

    api_key = os.environ.get("DEEPSEEK_PARAPHRASE_API_KEY")
    if not api_key:
        sys.exit("error: DEEPSEEK_PARAPHRASE_API_KEY is not set")
    if args.output.exists() and not args.force:
        sys.exit(f"error: {args.output} exists; pass --force to overwrite")

    text = args.input.read_text(encoding="utf-8")
    if not text.strip():
        sys.exit(f"error: {args.input} is empty")

    rewritten, usage = paraphrase(text, args.model, args.temperature, api_key)
    args.output.write_text(rewritten, encoding="utf-8")
    print(
        f"{args.output}  words {len(text.split())} -> {len(rewritten.split())}  "
        f"tokens in {usage['prompt_tokens']} out {usage['completion_tokens']}"
    )


if __name__ == "__main__":
    main()
