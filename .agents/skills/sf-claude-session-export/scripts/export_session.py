#!/usr/bin/env python3
"""Export a Claude Code session transcript to one Markdown file.

Reads the session's JSONL transcript and writes Obsidian-flavoured Markdown: frontmatter with
the session's metadata, a heading per turn, and thinking and tool calls folded into callouts.
Prints only the output path and counts, so the conversation never enters the agent's context.

Standard library only. Usage:
    export_session.py --list [N]
    export_session.py SESSION OUT [--max-result-chars N] [--force]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

CONVERSATION_TYPES = ("user", "assistant", "system")
FORBIDDEN_IN_FILENAME = re.compile(r'[\\/:#^\[\]|*"<>?\x00-\x1f]')


def projects_dir() -> Path:
    root = os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude"
    return Path(root) / "projects"


def find_transcript(session: str) -> Path:
    path = Path(session).expanduser()
    if path.suffix == ".jsonl":
        if not path.is_file():
            sys.exit(f"error: transcript not found: {path}")
        return path
    matches = sorted(projects_dir().glob(f"*/{session}.jsonl"))
    if not matches:
        sys.exit(f"error: no transcript for session {session} under {projects_dir()}")
    if len(matches) > 1:
        sys.exit(f"error: session {session} matches several transcripts: {matches}")
    return matches[0]


def load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main_chain(records: list[dict]) -> list[dict]:
    """The live conversation: walk back from the last message, skipping rewound branches.

    A compaction boundary has no parentUuid, only a logicalParentUuid pointing at the history
    it replaced, so the walk follows that to keep the full conversation.
    """
    by_uuid = {r["uuid"]: r for r in records if r.get("uuid")}
    leaf = next(
        (
            r
            for r in reversed(records)
            if r.get("type") in ("user", "assistant") and not r.get("isSidechain")
        ),
        None,
    )
    if leaf is None:
        sys.exit("error: transcript has no messages")
    chain, seen, node = [], set(), leaf
    while node is not None and node["uuid"] not in seen:
        seen.add(node["uuid"])
        chain.append(node)
        parent = node.get("parentUuid") or node.get("logicalParentUuid")
        node = by_uuid.get(parent)
    chain.reverse()
    return [r for r in chain if r.get("type") in CONVERSATION_TYPES]


def last_value(records: list[dict], rtype: str, key: str) -> str | None:
    return next((r[key] for r in reversed(records) if r.get("type") == rtype and r.get(key)), None)


def local_time(ts: str | None, fmt: str = "%Y-%m-%d %H:%M") -> str:
    if not ts:
        return ""
    return datetime.fromisoformat(ts).astimezone().strftime(fmt)


def fence(text: str, lang: str = "") -> str:
    longest = max((len(m) for m in re.findall(r"`+", text)), default=0)
    ticks = "`" * max(3, longest + 1)
    return f"{ticks}{lang}\n{text}\n{ticks}"


def callout(kind: str, title: str, body: str) -> str:
    quoted = "\n".join(f"> {line}" if line else ">" for line in body.rstrip().split("\n"))
    return f"> [!{kind}]- {title}\n{quoted}"


def truncate(text: str, limit: int) -> str:
    if limit and len(text) > limit:
        return f"{text[:limit]}\n… ({len(text) - limit} more characters)"
    return text


def result_text(content) -> str:
    if isinstance(content, str):
        return content
    parts = []
    for block in content or []:
        kind = block.get("type")
        if kind == "text":
            parts.append(block["text"])
        elif kind == "image":
            parts.append("[image]")
        elif kind == "tool_reference":
            parts.append(f"[loaded tool {block.get('tool_name')}]")
        else:
            parts.append(f"[{kind}]")
    return "\n".join(parts)


def tool_title(name: str, args: dict) -> str:
    for key in ("description", "file_path", "query", "url", "pattern", "skill", "command"):
        value = args.get(key)
        if isinstance(value, str) and value.strip():
            first = value.strip().split("\n")[0]
            return f"{name}: {first[:100]}"
    return name


def tool_input(name: str, args: dict) -> str:
    if name == "Bash" and "command" in args:
        return fence(args["command"], "bash")
    if name == "Write" and "content" in args:
        return fence(args["content"])
    if name == "Edit" and "old_string" in args:
        return fence(args["old_string"]) + "\n\n→\n\n" + fence(args.get("new_string", ""))
    return fence(json.dumps(args, indent=2, ensure_ascii=False), "json")


def user_text(content) -> str:
    text = (
        content
        if isinstance(content, str)
        else result_text([b for b in content if b.get("type") in ("text", "image")])
    )
    command = re.search(r"<command-name>(.*?)</command-name>", text, re.S)
    if command:
        args = re.search(r"<command-args>(.*?)</command-args>", text, re.S)
        return f"`{command.group(1).strip()} {args.group(1).strip() if args else ''}`".replace(
            " `", "`"
        )
    if text.startswith("[Request interrupted"):
        return f"*{text}*"
    return text


def render(records: list[dict], chain: list[dict], session_id: str, max_chars: int):
    results = {}
    for r in chain:
        content = r.get("message", {}).get("content")
        if r["type"] == "user" and isinstance(content, list):
            for block in content:
                if block.get("type") == "tool_result":
                    results[block["tool_use_id"]] = block

    title = last_value(records, "ai-title", "aiTitle") or f"Claude session {session_id}"
    messages = [r for r in chain if r["type"] in ("user", "assistant")]
    model = next(
        (
            r["message"].get("model")
            for r in messages
            if r["type"] == "assistant" and r["message"].get("model") != "<synthetic>"
        ),
        None,
    )
    bridge = last_value(records, "bridge-session", "bridgeSessionId")
    first = messages[0]
    meta = {
        "title": title,
        "session_id": session_id,
        "url": f"https://claude.ai/code/session_{bridge.removeprefix('cse_')}" if bridge else None,
        "resume": f"claude --resume {session_id}",
        "project": first.get("cwd"),
        "branch": first.get("gitBranch"),
        "model": model,
        "started": local_time(messages[0].get("timestamp"), "%Y-%m-%dT%H:%M:%S%z"),
        "ended": local_time(messages[-1].get("timestamp"), "%Y-%m-%dT%H:%M:%S%z"),
        "exported": datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "tags": ["claude-session"],
    }
    lines = ["---"]
    for key, value in meta.items():
        if value:
            lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    lines += ["---", "", f"# {title}"]

    counts = {"prompts": 0, "replies": 0, "tool calls": 0}
    speaker = None
    for r in chain:
        if r["type"] == "system":
            if r.get("subtype") == "compact_boundary":
                lines += ["", "---", "", "*Context compacted*"]
            continue
        content = r["message"].get("content")
        if r["type"] == "user":
            if r.get("isMeta"):
                continue
            if isinstance(content, list) and all(b.get("type") == "tool_result" for b in content):
                continue
            if r.get("isCompactSummary"):
                lines += [
                    "",
                    callout("abstract", "Summary of the compacted context", user_text(content)),
                ]
                continue
            stdout = re.fullmatch(
                r"\s*<local-command-(?:stdout|stderr)>(.*?)</local-command-(?:stdout|stderr)>\s*",
                content if isinstance(content, str) else "",
                re.S,
            )
            if stdout:
                lines += ["", callout("info", "Command output", fence(stdout.group(1).strip()))]
                continue
            counts["prompts"] += 1
            speaker = "user"
            lines += ["", f"## User · {local_time(r.get('timestamp'))}", "", user_text(content)]
            continue
        if speaker != "assistant":
            counts["replies"] += 1
            speaker = "assistant"
            lines += ["", f"## Claude · {local_time(r.get('timestamp'))}"]
        for block in content if isinstance(content, list) else [{"type": "text", "text": content}]:
            kind = block.get("type")
            if kind == "text" and block["text"].strip():
                lines += ["", block["text"]]
            elif kind == "thinking" and block.get("thinking", "").strip():
                lines += ["", callout("quote", "Thinking", block["thinking"])]
            elif kind == "tool_use":
                counts["tool calls"] += 1
                args = block.get("input") or {}
                body = tool_input(block["name"], args)
                result = results.get(block["id"])
                failed = bool(result and result.get("is_error"))
                if result:
                    output = truncate(result_text(result.get("content")), max_chars)
                    body += "\n\n" + ("Error:" if failed else "Result:") + "\n\n" + fence(output)
                kind_name = "failure" if failed else "example"
                lines += ["", callout(kind_name, tool_title(block["name"], args), body)]
    return title, "\n".join(lines) + "\n", counts


def output_path(out: str, title: str, started: str) -> Path:
    path = Path(out).expanduser()
    if path.is_dir():
        name = FORBIDDEN_IN_FILENAME.sub("", title).strip() or "Claude session"
        return path / f"{started} {name}.md"
    if not path.parent.is_dir():
        sys.exit(f"error: folder does not exist: {path.parent}")
    return path


def list_sessions(limit: int) -> None:
    files = sorted(projects_dir().glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in files[:limit]:
        records = load(path)
        title = last_value(records, "ai-title", "aiTitle") or "(untitled)"
        cwd = next((r["cwd"] for r in records if r.get("cwd")), "?")
        when = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"{path.stem}  {when}  {cwd}  {title}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("session", nargs="?", help="session ID, or a path to a .jsonl transcript")
    parser.add_argument("out", nargs="?", help="a folder, or the .md file to write")
    parser.add_argument(
        "--list",
        nargs="?",
        const=20,
        type=int,
        metavar="N",
        help="list the N most recently active sessions and exit",
    )
    parser.add_argument(
        "--max-result-chars",
        type=int,
        default=2000,
        metavar="N",
        help="truncate each tool result to N characters, 0 for no limit",
    )
    parser.add_argument("--force", action="store_true", help="overwrite an existing file")
    args = parser.parse_args()

    if args.list is not None:
        list_sessions(args.list)
        return
    if not args.session or not args.out:
        parser.error("SESSION and OUT are required unless --list is given")

    transcript = find_transcript(args.session)
    records = load(transcript)
    chain = main_chain(records)
    title, markdown, counts = render(records, chain, transcript.stem, args.max_result_chars)
    started = local_time(chain[0].get("timestamp"), "%Y-%m-%d")
    path = output_path(args.out, title, started)
    if path.exists() and not args.force:
        sys.exit(f"error: {path} exists; pass --force to overwrite")
    path.write_text(markdown, encoding="utf-8")
    print(path)
    print(", ".join(f"{n} {k}" for k, n in counts.items()))


if __name__ == "__main__":
    main()
