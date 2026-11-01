#!/usr/bin/env python3
"""Keep live flowcharts of a codebase's architecture honest against the code they describe.

The agent draws Mermaid. This script refuses anything the repository doesn't back up, records every
change in an event log per diagram, and replays the log into an immutable JSON snapshot for the
page. Progress is a layer on the chart: a box is always a piece of the code, never a task.

Standard library only. Linux and macOS (uses fcntl). Run `flow.py --help` for commands.
"""

from __future__ import annotations

import argparse
import contextlib
import difflib
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

SCHEMA = 3
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
HEADER_RE = re.compile(r"^(?:flowchart|graph)(?:\s+(\w+))?$")
SHAPES = [
    ("([", "])", "terminal"),
    ("[(", ")]", "table"),
    ("[/", "/]", "io"),
    ("[", "]", "box"),
    ("{", "}", "decision"),
]
SHAPE_HELP = "id[box], id([start or end]), id{decision}, id[(table)], id[/input or output/]"
EDGES = [
    (re.compile(r"^\s*-->\s*(?:\|([^|]*)\|)?"), "solid"),
    (re.compile(r"^\s*-\.->\s*(?:\|([^|]*)\|)?"), "dashed"),
    (re.compile(r"^\s*==>\s*(?:\|([^|]*)\|)?"), "thick"),
    (re.compile(r"^\s*--\s+([^>]+?)\s+-->"), "solid"),
    (re.compile(r"^\s*-\.\s+([^>]+?)\s+\.->"), "dashed"),
]
DEFINITION_WORDS = "def|class|function|const|let|var|fn|func|type|interface|struct|enum"
SQL_DEFINITION = r"(?i:create\s+(?:table|view)(?:\s+if\s+not\s+exists)?)"
ACTIVITY_EVENTS = {"edit", "compared"}
EDIT_TOOLS = {"Edit", "Write", "NotebookEdit"}
SKIPPED_DIRS = {".git", "__pycache__", "node_modules", ".venv"}
GLYPHS = {"planned": "[ ]", "active": "[>]", "built": "[=]", "failed": "[x]"}
CLOSERS = ("}", ")", "]", "end")
CHECK_TAIL_CHARS = 2000
CHECK_TIMEOUT_SECONDS = 600
MAX_EVENTS_IN_SNAPSHOT = 60
MAX_FILES_PER_BOX = 30
MAX_COMPARISONS = 5
MAX_DIFF_CHARS = 1500
MAX_DIFFS_CHARS = 30_000
MAX_OTHER_FILES = 40
MAX_SNAPSHOT_BYTES = 240_000
KEEP_SNAPSHOTS = 50
WATCH_POLL_SECONDS = 1.0
VIEW_CAPABILITIES = {
    "db": {"rules": [{"path": "diagrams", "read": "view", "write": "admin"}]},
    "comments": {},
}


class FlowError(Exception):
    """A refused operation. The message says what was refused and what to do."""


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


# Parsing


def unquote(text: str) -> str:
    text = text.strip()
    return text[1:-1] if len(text) > 1 and text[0] == text[-1] == '"' else text


def split_label(raw: str) -> tuple[str, str | None]:
    title, *rest = re.split(r"<br\s*/?>", unquote(raw), flags=re.IGNORECASE)
    return title.strip(), " ".join(part.strip() for part in rest).strip() or None


def read_node(graph: dict, text: str, pos: int, number: int, group: str | None) -> tuple[str, int]:
    match = re.match(r"\s*([A-Za-z_]\w*)", text[pos:])
    if not match:
        raise FlowError(f"line {number}: expected a box id at `{text[pos:].strip()}`")
    node_id = match.group(1)
    pos += match.end()
    if text.startswith("(", pos) and not text.startswith("([", pos):
        raise FlowError(f"line {number}: `{node_id}` uses an unsupported shape. Use {SHAPE_HELP}")
    for opening, closing, shape in SHAPES:
        if not text.startswith(opening, pos):
            continue
        start = pos + len(opening)
        quoted = re.match(r"\s*\"", text[start:])
        shut = text.find('"', start + quoted.end()) if quoted else -1
        end = text.find(closing, shut + 1 if shut >= 0 else start)
        if end < 0:
            raise FlowError(f"line {number}: `{node_id}` is missing its closing `{closing}`")
        if node_id in graph["nodes"]:
            raise FlowError(f"line {number}: box `{node_id}` is declared twice")
        title, sub = split_label(text[start:end])
        if not title:
            raise FlowError(f"line {number}: box `{node_id}` has no label")
        graph["nodes"][node_id] = {
            "id": node_id,
            "shape": shape,
            "title": title,
            "sub": sub,
            "group": group,
            "ref": None,
            "check": None,
            "planned": False,
        }
        return node_id, end + len(closing)
    return node_id, pos


def read_statement(graph: dict, text: str, number: int, group: str | None) -> None:
    source, pos = read_node(graph, text, 0, number, group)
    while pos < len(text.rstrip()):
        found = ((pattern.match(text[pos:]), style) for pattern, style in EDGES)
        match, style = next((pair for pair in found if pair[0]), (None, None))
        if not match:
            raise FlowError(f"line {number}: can't read `{text[pos:].strip()}`")
        target, pos = read_node(graph, text, pos + match.end(), number, group)
        label = (match.group(1) or "").strip() or None
        graph["edges"].append(
            {"from": source, "to": target, "label": label, "style": style, "line": number}
        )
        source = target


def parse_diagram(text: str) -> dict:
    """Parse the Mermaid subset, and refuse every line it can't honour rather than ignore it."""
    graph: dict = {"title": None, "nodes": {}, "edges": [], "groups": []}
    lines = text.splitlines()
    index = next((i for i, line in enumerate(lines) if line.strip()), 0)
    if index < len(lines) and lines[index].strip() == "---":
        index += 1
        while index < len(lines) and lines[index].strip() != "---":
            match = re.match(r"^title:\s*(.+)$", lines[index].strip())
            if match:
                graph["title"] = unquote(match.group(1))
            index += 1
        index += 1
    if not graph["title"]:
        raise FlowError("the diagram needs frontmatter with a title: ---, title: ..., ---")
    seen_header = False
    groups: list[str] = []
    metadata: list[tuple[int, str, str, str]] = []
    planned: list[tuple[int, str]] = []
    for offset, raw in enumerate(lines[index:], index + 1):
        line = raw.strip().removesuffix(";").strip()
        if not line:
            continue
        match = re.match(r"^%%\s*(code|check):\s*(\S+)\s+(\S.*?)\s*$", line)
        if match:
            metadata.append((offset, match.group(1), match.group(2), match.group(3)))
            continue
        if line.startswith("%%"):
            continue
        header = HEADER_RE.match(line)
        if header:
            if seen_header:
                raise FlowError(f"line {offset}: the flowchart header appears twice")
            if header.group(1) not in (None, "TD", "TB"):
                raise FlowError(f"line {offset}: charts run top to bottom. Use `flowchart TD`")
            seen_header = True
            continue
        if not seen_header:
            raise FlowError(f"line {offset}: expected `flowchart TD` first")
        match = re.match(r'^subgraph\s+([\w-]+)\s*(?:\[\s*"?(.*?)"?\s*\])?$', line)
        if match:
            title = match.group(2) or match.group(1)
            parent = groups[-1] if groups else None
            graph["groups"].append({"id": match.group(1), "title": title, "parent": parent})
            groups.append(match.group(1))
            continue
        if line == "end":
            if not groups:
                raise FlowError(f"line {offset}: `end` has no matching subgraph")
            groups.pop()
            continue
        match = re.match(r"^class\s+([\w,\s-]+?)\s+(\w+)$", line)
        if match:
            if match.group(2) != "planned":
                raise FlowError(
                    f"line {offset}: only `class <ids> planned` is allowed. "
                    "`flow.py begin` and `flow.py done` set every other status"
                )
            planned += [(offset, item.strip()) for item in match.group(1).split(",")]
            continue
        if re.match(r"^(classDef|style|linkStyle|click|direction)\b", line):
            raise FlowError(
                f"line {offset}: `{line.split()[0]}` isn't supported: the page styles it"
            )
        read_statement(graph, line, offset, groups[-1] if groups else None)
    if not seen_header:
        raise FlowError("the diagram needs a `flowchart TD` line")
    if groups:
        raise FlowError(f"subgraph `{groups[-1]}` has no matching `end`")
    for number, kind, node_id, value in metadata:
        if node_id not in graph["nodes"]:
            raise FlowError(f"line {number}: `%% {kind}` names unknown box `{node_id}`")
        graph["nodes"][node_id]["ref" if kind == "code" else "check"] = value
    for number, node_id in planned:
        if node_id not in graph["nodes"]:
            raise FlowError(f"line {number}: `class` names unknown box `{node_id}`")
        graph["nodes"][node_id]["planned"] = True
    validate_graph(graph)
    graph["nodes"] = list(graph["nodes"].values())
    for edge in graph["edges"]:
        del edge["line"]
    return graph


def validate_graph(graph: dict) -> None:
    nodes = graph["nodes"]
    if not nodes:
        raise FlowError("the diagram has no boxes")
    for edge in graph["edges"]:
        for end in (edge["from"], edge["to"]):
            if end not in nodes:
                raise FlowError(
                    f"line {edge['line']}: `{end}` has no shape. Declare it once: {SHAPE_HELP}"
                )
    connected = {end for edge in graph["edges"] for end in (edge["from"], edge["to"])}
    if len(nodes) > 1:
        orphans = sorted(set(nodes) - connected)
        if orphans:
            raise FlowError(f"boxes with no arrows: {', '.join(orphans)}. Connect or remove them")
    table_refs: dict[str, str] = {}
    for node in nodes.values():
        exits = [edge for edge in graph["edges"] if edge["from"] == node["id"]]
        if node["shape"] == "decision":
            labels = [edge["label"] for edge in exits]
            if len(exits) < 2 or None in labels or len(set(labels)) != len(labels):
                raise FlowError(
                    f"decision `{node['id']}` needs at least two exits with different labels: "
                    f"{node['id']} -->|yes| next"
                )
        if node["shape"] == "table":
            if not node["ref"] or ":" not in node["ref"]:
                raise FlowError(
                    f"table `{node['id']}` needs `%% code: {node['id']} <path>:<table name>`. "
                    "A cylinder means a real database table"
                )
            if node["ref"] in table_refs:
                raise FlowError(
                    f"tables `{table_refs[node['ref']]}` and `{node['id']}` share {node['ref']}. "
                    "Draw one cylinder per table"
                )
            table_refs[node["ref"]] = node["id"]
        if node["shape"] != "terminal" and not node["ref"] and not node["planned"]:
            raise FlowError(
                f"box `{node['id']}` isn't tied to code. Add "
                f"`%% code: {node['id']} <path>:<symbol>`, "
                f"or `class {node['id']} planned` if it doesn't exist yet"
            )


# References into the code


def project_root(start: Path) -> Path:
    found = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    return Path(found.stdout.strip()) if found.returncode == 0 else start.resolve()


def block_end(lines: list[str], start: int) -> int:
    """Where a definition's block stops, by indentation, so this works in any language."""
    indent = len(lines[start]) - len(lines[start].lstrip())
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if not stripped:
            continue
        if len(lines[index]) - len(lines[index].lstrip()) <= indent:
            return index + 1 if stripped.startswith(CLOSERS) else index
    return len(lines)


def digest_directory(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(path.rglob("*")):
        if item.is_file() and not SKIPPED_DIRS.intersection(item.parts):
            digest.update(str(item.relative_to(path)).encode())
            digest.update(item.read_bytes())
    return digest.hexdigest()[:16]


def split_ref(ref: str) -> tuple[str, str, str]:
    """`path:symbol > text` names a file, a definition in it, and a line inside that."""
    location, _, anchor = ref.partition(" > ")
    path_text, separator, symbol = location.strip().partition(":")
    if separator and symbol.isdigit():
        raise FlowError(f"{ref}: refer to a symbol, not a line number, because lines move")
    return path_text, symbol, anchor.strip()


def locate(text: str, ref: str) -> tuple[int | None, str, str]:
    """Find what a ref points at in a file's text. Returns its line, code hash and code."""
    path_text, symbol, anchor = split_ref(ref)
    lines = text.splitlines()
    start, end = 0, len(lines)
    if symbol:
        name = re.escape(symbol)
        definition = re.compile(
            rf"\b(?:{DEFINITION_WORDS}|{SQL_DEFINITION})\s+[\"'`]?{name}(?![\w])"
            rf"|^\s*{name}\s*[:=(]"
        )
        mention = re.compile(rf"(?<![\w]){name}(?![\w])")
        found = next((i for i, line in enumerate(lines) if definition.search(line)), None)
        if found is None:
            found = next((i for i, line in enumerate(lines) if mention.search(line)), None)
        if found is None:
            raise FlowError(f"{ref}: `{symbol}` doesn't appear in {path_text}")
        start, end = found, block_end(lines, found)
    if anchor:
        found = next((i for i in range(start, end) if anchor in lines[i]), None)
        if found is None:
            where = f"`{symbol}`" if symbol else path_text
            raise FlowError(f"{ref}: `{anchor}` doesn't appear in {where}")
        start, end = found, block_end(lines, found)
    if not symbol and not anchor:
        return None, hashlib.sha256(text.encode()).hexdigest()[:16], text
    # Blank lines after a block belong to whatever follows it, so they don't count as its code.
    block = "\n".join(lines[start:end]).rstrip()
    return start + 1, hashlib.sha256(block.encode()).hexdigest()[:16], block


def resolve_ref(root: Path, ref: str) -> dict:
    """Find what a ref points at and hash it. Raises when the repository has no such thing."""
    path_text, symbol, anchor = split_ref(ref)
    path = (root / path_text).resolve()
    if not path.is_relative_to(root):
        raise FlowError(f"{ref}: the path is outside the project")
    if not path.exists():
        raise FlowError(f"{ref}: {path_text} doesn't exist")
    if path.is_dir():
        if symbol or anchor:
            raise FlowError(f"{ref}: {path_text} is a folder, so it can't hold a symbol")
        return {"path": path_text, "symbol": None, "line": None, "hash": digest_directory(path)}
    line, digest, _ = locate(path.read_text(errors="replace"), ref)
    return {"path": path_text, "symbol": symbol or None, "line": line, "hash": digest}


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)


def current_branch(root: Path) -> str | None:
    found = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    return found.stdout.strip() if found.returncode == 0 else None


def base_commit(root: Path) -> str | None:
    """Where this branch began: its fork from the default branch, or HEAD if it is that branch."""
    head = git(root, "rev-parse", "--verify", "--quiet", "HEAD^{commit}")
    if head.returncode != 0:
        return None
    origin = git(root, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    names = [origin.stdout.strip()] if origin.returncode == 0 else []
    for name in [*names, "main", "master"]:
        fork = git(root, "merge-base", "HEAD", name)
        if fork.returncode == 0:
            return fork.stdout.strip()
    return head.stdout.strip()


def format_diff(old: str, new: str) -> str:
    lines = difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="", n=2)
    return "\n".join(list(lines)[2:])


def compare_box(root: Path, commit: str, ref: str) -> tuple[str, str] | None:
    """How the code behind a ref differs from a commit: (added or changed, its diff), or None."""
    path_text, symbol, anchor = split_ref(ref)
    kind = git(root, "cat-file", "-t", f"{commit}:{path_text}")
    current = root / path_text
    if kind.returncode != 0:
        if current.is_file():
            try:
                return "added", format_diff("", locate(current.read_text(errors="replace"), ref)[2])
            except FlowError:
                return "added", ""
        return "added", ""
    if not symbol and not anchor:
        change = git(root, "diff", commit, "--", path_text).stdout
        return ("changed", "\n".join(change.splitlines()[4:])) if change else None
    old = git(root, "show", f"{commit}:{path_text}").stdout
    try:
        _, old_hash, old_block = locate(old, ref)
    except FlowError:
        new_block = locate(current.read_text(errors="replace"), ref)[2]
        return "added", format_diff("", new_block)
    try:
        _, new_hash, new_block = locate(current.read_text(errors="replace"), ref)
    except (FlowError, OSError):
        return "changed", format_diff(old_block, "")
    return None if new_hash == old_hash else ("changed", format_diff(old_block, new_block))


def changed_files(root: Path, commit: str) -> list[dict]:
    """Every file that differs from a commit, including ones git doesn't track yet."""
    files = []
    for line in git(root, "diff", "--name-status", commit).stdout.splitlines():
        status, *paths = line.split("\t")
        files.append({"path": paths[-1], "status": status[0]})
    untracked = git(root, "ls-files", "--others", "--exclude-standard").stdout.splitlines()
    return files + [{"path": path, "status": "A"} for path in untracked]


# Storage


def state_home() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "sf-live-flowchart"


def project_dir(root: Path) -> Path:
    digest = hashlib.sha256(str(root).encode()).hexdigest()[:8]
    return state_home() / f"{root.name}-{digest}"


def read_json(path: Path, default: dict) -> dict:
    return json.loads(path.read_text()) if path.exists() else default


def write_atomic(path: Path, text: str) -> None:
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(text)
    temp.replace(path)


def diagram_dirs(project: Path) -> list[Path]:
    folder = project / "diagrams"
    return sorted(item for item in folder.iterdir() if item.is_dir()) if folder.is_dir() else []


def diagram_dir(project: Path, diagram: str) -> Path:
    path = project / "diagrams" / diagram
    if not path.is_dir():
        known = ", ".join(item.name for item in diagram_dirs(project)) or "none"
        raise FlowError(
            f"no diagram `{diagram}`. Diagrams: {known}. Create one with `flow.py draw`"
        )
    return path


@contextlib.contextmanager
def locked(folder: Path):
    with (folder / "lock").open("w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def read_events(folder: Path) -> list[dict]:
    log = folder / "events.jsonl"
    events = []
    for number, line in enumerate(log.read_text().splitlines(), 1):
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise FlowError(f"{log}:{number} is not valid JSON: {error}") from error
    return events


# Replay


def new_node(definition: dict, status: str) -> dict:
    return {
        "id": definition["id"],
        "shape": definition["shape"],
        "title": definition["title"],
        "sub": definition["sub"],
        "group": definition["group"],
        "ref": definition["ref"],
        "check": definition["check"],
        "status": status,
        "current": False,
        "changed": False,
        "result": None,
        "resolved": None,
        "stale": False,
        "broken": False,
        "agent": None,
        "startedAt": None,
        "finishedAt": None,
        "lastEventAt": None,
        "attempts": 0,
        "checkResult": None,
        "notes": [],
        "touched": [],
    }


def describe(event: dict) -> str:
    kind, node = event["type"], event.get("node")
    if kind == "drawn":
        return f"Drew {len(event['graph']['nodes'])} boxes"
    if kind == "begun":
        return f"{node} started" + (f" by {event['agent']}" if event.get("agent") else "")
    if kind == "done":
        return f"{node} built, check passed" if "exit" in event else f"{node} built, no check"
    if kind == "failed":
        return f"{node} check exited {event['exit']}" if "exit" in event else f"{node} failed"
    if kind == "stale":
        return f"{node} was edited after the chart was drawn, so it needs review"
    if kind == "broken":
        return f"{node} no longer resolves: {event['reason']}"
    if kind == "fresh":
        return f"{node} matches the code again"
    if kind == "confirmed":
        return f"{node} confirmed against the code"
    if kind == "note":
        return f"{node} note"
    if kind == "context":
        return f"Topic set: {event['topic']}"
    if kind == "compared":
        return f"Compared with {event['short']}: {len(event['states'])} boxes differ"
    if kind == "edit":
        boxes = ", ".join(event["nodes"]) or "no box"
        return f"{event['file']} edited ({boxes})"
    raise FlowError(f"unknown event type `{kind}` in the log")


def apply_drawn(diagram: dict, event: dict) -> None:
    graph, previous = event["graph"], {node["id"]: node for node in diagram["nodes"]}
    drawn = {definition["id"] for definition in graph["nodes"]}
    kept = [item for item in diagram["removedBoxes"] if item["id"] not in drawn]
    gone = [
        {"id": node["id"], "title": node["title"], "at": event["at"]}
        for node in diagram["nodes"]
        if node["id"] not in drawn
    ]
    diagram["removedBoxes"] = kept + gone
    nodes = []
    for definition in graph["nodes"]:
        old = previous.get(definition["id"])
        node = new_node(definition, "planned" if definition["planned"] else "built")
        if old:
            fixed = {*definition, "resolved", "stale", "broken"}
            node.update({key: old[key] for key in node if key not in fixed})
        node["resolved"] = event["resolved"].get(definition["id"])
        nodes.append(node)
    diagram.update(title=graph["title"], edges=graph["edges"], groups=graph["groups"], nodes=nodes)
    diagram["root"] = event.get("root")


def apply_event(diagram: dict, event: dict) -> None:
    kind, at = event["type"], event["at"]
    nodes = {node["id"]: node for node in diagram["nodes"]}
    node = nodes.get(event.get("node"))
    if node is not None:
        node["lastEventAt"] = at
        if event.get("note"):
            node["notes"].append({"at": at, "text": event["note"]})
    if kind == "begun":
        node.update(
            status="active",
            agent=event.get("agent"),
            startedAt=at,
            finishedAt=None,
            attempts=node["attempts"] + 1,
            stale=False,
            broken=False,
            changed=True,
        )
    elif kind in {"done", "failed"}:
        if "exit" in event:
            node["checkResult"] = {
                "at": at,
                "command": event["command"],
                "exit": event["exit"],
                "tail": event["tail"],
                "seconds": event["seconds"],
            }
        if kind == "done":
            result = "verified" if "exit" in event else "claimed"
            node.update(status="built", result=result, resolved=event["resolved"], finishedAt=at)
        else:
            node.update(status="failed", finishedAt=at)
    elif kind == "stale":
        node.update(stale=True)
    elif kind == "broken":
        node.update(broken=True, stale=False)
    elif kind == "fresh":
        node.update(stale=False, broken=False)
    elif kind == "confirmed":
        node.update(stale=False, broken=False, resolved=event["resolved"])
    elif kind == "note":
        node["notes"].append({"at": at, "text": event["text"]})
    elif kind == "compared":
        auto = event.get("auto", False)
        others = [
            item
            for item in diagram["comparisons"]
            if item["commit"] != event["commit"] and not (auto and item["auto"])
        ]
        entry = {
            "commit": event["commit"],
            "short": event["short"],
            "subject": event["subject"],
            "auto": auto,
            "states": event["states"],
            "diffs": event.get("diffs", {}),
            "files": event.get("files", []),
            "filesTotal": event.get("filesTotal", 0),
            "removed": event.get("removed", []),
        }
        diagram["comparisons"] = [entry, *others][:MAX_COMPARISONS]
    elif kind == "edit":
        for node_id in event["nodes"]:
            touched = nodes[node_id]["touched"]
            if event["file"] not in touched:
                touched.append(event["file"])
                del touched[:-MAX_FILES_PER_BOX]
        if not event["nodes"] and event["file"] not in diagram["unmapped"]:
            diagram["unmapped"].append(event["file"])


def fold(events: list[dict]) -> dict:
    """Replay the log into the document the page renders. Pure: same log, same document."""
    head = events[0]
    diagram = {
        "schema": SCHEMA,
        "id": head["diagram"],
        "root": None,
        "branch": None,
        "topic": None,
        "title": head["graph"]["title"],
        "createdAt": head["at"],
        "updatedAt": head["at"],
        "seq": 0,
        "lastTransitionSeq": 0,
        "nodes": [],
        "edges": [],
        "groups": [],
        "unmapped": [],
        "comparisons": [],
        "removedBoxes": [],
        "events": [],
    }
    latest_begun = None
    for event in events:
        diagram["seq"], diagram["updatedAt"] = event["seq"], event["at"]
        diagram["branch"], diagram["topic"] = event.get("branch"), event.get("topic")
        if event["type"] not in ACTIVITY_EVENTS:
            diagram["lastTransitionSeq"] = event["seq"]
        if event["type"] == "drawn":
            apply_drawn(diagram, event)
        else:
            apply_event(diagram, event)
        if event["type"] == "begun":
            latest_begun = event["node"]
        diagram["events"].append({"seq": event["seq"], "at": event["at"], "text": describe(event)})
    for node in diagram["nodes"]:
        node["current"] = node["id"] == latest_begun and node["status"] == "active"
    del diagram["events"][:-MAX_EVENTS_IN_SNAPSHOT]
    return diagram


def write_snapshot(folder: Path, diagram: dict) -> None:
    text = json.dumps(diagram, separators=(",", ":"))
    if len(text.encode()) > MAX_SNAPSHOT_BYTES:
        raise FlowError(
            f"diagram `{diagram['id']}` is {len(text.encode())} bytes, over the "
            f"{MAX_SNAPSHOT_BYTES} limit for one artifact document: split it into two diagrams"
        )
    snapshots = folder / "snapshots"
    snapshots.mkdir(exist_ok=True)
    write_atomic(snapshots / f"{diagram['seq']}.json", text)
    kept = sorted(snapshots.glob("*.json"), key=lambda item: int(item.stem))
    for old in kept[:-KEEP_SNAPSHOTS]:
        old.unlink()


def append(folder: Path, event: dict) -> dict:
    """Add one event and write its snapshot. The caller holds the lock."""
    log = folder / "events.jsonl"
    events = read_events(folder) if log.exists() else []
    meta = read_json(folder.parent.parent / "project.json", {})
    context = {"branch": current_branch(Path(meta["path"])), "topic": meta.get("topic")}
    event = {"seq": len(events) + 1, "at": now(), **context, **event}
    events.append(event)
    diagram = fold(events)
    write_snapshot(folder, diagram)
    with log.open("a") as handle:
        handle.write(json.dumps(event) + "\n")
    return diagram


def load(folder: Path) -> dict:
    return fold(read_events(folder))


def find_node(diagram: dict, node_id: str) -> dict:
    for node in diagram["nodes"]:
        if node["id"] == node_id:
            return node
    known = ", ".join(node["id"] for node in diagram["nodes"])
    raise FlowError(f"diagram `{diagram['id']}` has no box `{node_id}`. Boxes: {known}")


# Comparing the chart with the code


def scan(folder: Path, root: Path, only: set[str] | None = None) -> dict:
    """Log any box whose code moved. A box being worked on is expected to change."""
    diagram = load(folder)
    for node in diagram["nodes"]:
        if only is not None and node["id"] not in only:
            continue
        if not node["ref"] or node["status"] != "built" or not node["resolved"]:
            continue
        try:
            found = resolve_ref(root, node["ref"])
        except FlowError as error:
            if not node["broken"]:
                diagram = append(
                    folder, {"type": "broken", "node": node["id"], "reason": str(error)}
                )
            continue
        matches = found["hash"] == node["resolved"]["hash"]
        if matches and (node["stale"] or node["broken"]):
            diagram = append(folder, {"type": "fresh", "node": node["id"]})
        elif not matches and not node["stale"]:
            diagram = append(folder, {"type": "stale", "node": node["id"]})
    return diagram


def scan_all(folders: list[Path], root: Path) -> None:
    for folder in folders:
        with locked(folder):
            scan(folder, root)
            refresh_base(folder, root)


def build_comparison(root: Path, commit: str, diagram: dict) -> dict:
    """Everything that differs from a commit: boxes with their diffs, other files, removed boxes."""
    show = git(root, "log", "-1", "--format=%ct%x00%s", commit).stdout.strip()
    stamp, _, subject = show.partition("\0")
    states, diffs = {}, {}
    budget = MAX_DIFFS_CHARS
    for node in diagram["nodes"]:
        if not node["ref"] or not node["resolved"]:
            continue
        found = compare_box(root, commit, node["ref"])
        if not found:
            continue
        states[node["id"]], diff = found
        diff = diff[:MAX_DIFF_CHARS]
        if diff and len(diff) <= budget:
            diffs[node["id"]] = diff
            budget -= len(diff)
    others = [
        item
        for item in changed_files(root, commit)
        if not any(covers(node, item["path"]) for node in diagram["nodes"])
    ]
    removed = [
        {"id": item["id"], "title": item["title"]}
        for item in diagram["removedBoxes"]
        if datetime.fromisoformat(item["at"]).timestamp() >= int(stamp)
    ]
    return {
        "type": "compared",
        "commit": commit,
        "short": commit[:7],
        "subject": subject,
        "auto": commit == base_commit(root),
        "states": states,
        "diffs": diffs,
        "files": others[:MAX_OTHER_FILES],
        "filesTotal": len(others),
        "removed": removed,
    }


def refresh_base(folder: Path, root: Path) -> dict | None:
    """Keep the comparison with the branch start current. The caller holds the lock."""
    commit = base_commit(root)
    if commit is None:
        return None
    untracked = git(root, "ls-files", "--others", "--exclude-standard").stdout.splitlines()
    stamps = [(path, (root / path).stat().st_mtime_ns) for path in untracked]
    log = (folder / "events.jsonl").read_bytes()
    drawn = [line for line in log.splitlines() if b'"type": "drawn"' in line]
    state = [commit, git(root, "diff", commit).stdout, stamps, len(drawn)]
    signature = hashlib.sha256(json.dumps(state).encode()).hexdigest()
    marker = folder / "compare.sig"
    if marker.exists() and marker.read_text() == signature:
        return None
    diagram = load(folder)
    event = build_comparison(root, commit, diagram)
    write_atomic(marker, signature)
    keys = ("states", "diffs", "files", "filesTotal", "removed")
    for item in diagram["comparisons"]:
        if item["commit"] == commit and all(item[key] == event[key] for key in keys):
            return None
    return append(folder, event)


# Pushing to the artifact


def push_state(folder: Path) -> dict:
    return read_json(folder / "push.json", {"seq": 0, "version": None})


def push_line(folder: Path, diagram: dict) -> str | None:
    """The exact tool call that sends the newest snapshot, or None when nothing is waiting."""
    pushed = push_state(folder)
    if pushed["seq"] >= diagram["seq"]:
        return None
    url = read_json(folder.parent.parent / "project.json", {}).get("url")
    if url is None:
        return "PUSH blocked: publish the page first, then run `flow.py link <url>`."
    path = folder / "snapshots" / f"{diagram['seq']}.json"
    version = "" if pushed["version"] is None else f" if_version={pushed['version']}"
    return (
        f"PUSH seq={diagram['seq']}: ArtifactData action=set url={url} collection=diagrams "
        f"doc_id={diagram['id']} file_path={path}{version}"
    )


def report(folder: Path, diagram: dict, *lines: str) -> None:
    for line in lines:
        print(line)
    line = push_line(folder, diagram)
    if line:
        print(line)


def record_push(folder: Path, seq: int, version: int) -> None:
    with locked(folder):
        pushed = push_state(folder)
        if version < (pushed["version"] or 0):
            raise FlowError(f"version {version} is older than the recorded {pushed['version']}")
        write_atomic(
            folder / "push.json",
            json.dumps({"seq": max(seq, pushed["seq"]), "version": version}) + "\n",
        )


# Commands


def template_path() -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / "view.html"


def publish_lines(project: Path, root: Path) -> list[str]:
    """Copy the page beside the project and say how to publish it, when that is needed."""
    project.mkdir(parents=True, exist_ok=True)
    meta_path = project / "project.json"
    meta = read_json(meta_path, {"path": str(root), "url": None, "viewSha": None})
    template_sha = hashlib.sha256(template_path().read_bytes()).hexdigest()
    lines = []
    if meta["url"] is None or meta["viewSha"] != template_sha:
        view = project / "view.html"
        shutil.copyfile(template_path(), view)
        meta["viewSha"] = template_sha if meta["url"] else None
        target = f" url={meta['url']}" if meta["url"] else " icon=flowchart"
        lines.append(
            f"PUBLISH: Artifact action=publish file_path={view}{target} "
            f"capabilities={json.dumps(VIEW_CAPABILITIES, separators=(',', ':'))}"
        )
        if not meta["url"]:
            lines.append("Then run `flow.py link <url>` with the URL it returns.")
    else:
        lines.append(f"Live view: {meta['url']}")
    write_atomic(meta_path, json.dumps(meta, indent=2) + "\n")
    return lines


def command_draw(args: argparse.Namespace, project: Path, root: Path) -> None:
    if not SLUG_RE.match(args.diagram):
        raise FlowError(f"diagram name `{args.diagram}` must be lower-kebab-case")
    source = sys.stdin.read()
    graph = parse_diagram(source)
    resolved = {}
    for node in graph["nodes"]:
        if not node["ref"]:
            continue
        try:
            resolved[node["id"]] = resolve_ref(root, node["ref"])
        except FlowError as error:
            if not node["planned"]:
                raise FlowError(
                    f"box `{node['id']}`: {error}. Fix the ref, or mark it "
                    f"`class {node['id']} planned` if it doesn't exist yet"
                ) from error
    lines = publish_lines(project, root)
    folder = project / "diagrams" / args.diagram
    folder.mkdir(parents=True, exist_ok=True)
    with locked(folder):
        if (folder / "events.jsonl").exists():
            old = {node["id"]: node for node in load(folder)["nodes"]}
            for node in graph["nodes"]:
                previous = old.get(node["id"])
                if node["planned"] and previous and previous["status"] != "planned":
                    raise FlowError(
                        f"box `{node['id']}` is {previous['status']}, so it can't go back to "
                        "planned. Use `flow.py begin` to change it"
                    )
        diagram = append(
            folder,
            {
                "type": "drawn",
                "diagram": args.diagram,
                "root": str(root),
                "graph": graph,
                "resolved": resolved,
            },
        )
        write_atomic(folder / "source.mmd", source)
        diagram = refresh_base(folder, root) or diagram
    # Hook commands can't locate the skill, so they run this copy at a fixed path.
    write_atomic(state_home() / "flow.py", Path(__file__).read_text())
    counts = f"{len(graph['nodes'])} boxes, {len(graph['edges'])} arrows"
    report(folder, diagram, f"Drew {args.diagram}: {counts}.", *lines)


def command_link(args: argparse.Namespace, project: Path, root: Path) -> None:
    if not re.match(r"^https://claude\.ai/(code/)?artifact/[\w-]+$", args.url):
        raise FlowError(f"{args.url} is not a claude.ai artifact URL")
    meta_path = project / "project.json"
    if not meta_path.exists():
        raise FlowError(f"no project at {project}: run `flow.py draw` first")
    meta = read_json(meta_path, {})
    meta.update(url=args.url, viewSha=hashlib.sha256(template_path().read_bytes()).hexdigest())
    write_atomic(meta_path, json.dumps(meta, indent=2) + "\n")
    print(f"Linked {args.url}")
    for folder in diagram_dirs(project):
        line = push_line(folder, load(folder))
        if line:
            print(line)


def command_topic(args: argparse.Namespace, project: Path, root: Path) -> None:
    meta_path = project / "project.json"
    if not meta_path.exists():
        raise FlowError(f"no project at {project}: run `flow.py draw` first")
    meta = read_json(meta_path, {})
    meta["topic"] = args.text
    write_atomic(meta_path, json.dumps(meta, indent=2) + "\n")
    print(f"Topic: {args.text}")
    for folder in diagram_dirs(project):
        with locked(folder):
            diagram = append(folder, {"type": "context", "topic": args.text})
        line = push_line(folder, diagram)
        if line:
            print(line)


def command_begin(args: argparse.Namespace, project: Path, root: Path) -> None:
    folder = diagram_dir(project, args.diagram)
    with locked(folder):
        node = find_node(load(folder), args.box)
        if node["status"] == "active":
            raise FlowError(f"box `{args.box}` is already active")
        diagram = append(
            folder, {"type": "begun", "node": args.box, "agent": args.agent, "note": args.note}
        )
    report(folder, diagram, f"{args.box}: active")


def run_check(command: str, root: Path, timeout: int) -> tuple[int, str, float]:
    started = time.monotonic()
    try:
        finished = subprocess.run(
            command,
            shell=True,
            cwd=root,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
        )
        code, output = finished.returncode, finished.stdout + finished.stderr
    except subprocess.TimeoutExpired as error:
        partial = error.stdout or b""
        code = 124
        output = partial.decode(errors="replace") + f"\nTimed out after {timeout} seconds."
    return code, output[-CHECK_TAIL_CHARS:], round(time.monotonic() - started, 1)


def require_active(diagram: dict, box: str, action: str) -> dict:
    node = find_node(diagram, box)
    if node["status"] != "active":
        raise FlowError(f"cannot {action} `{box}`: it is {node['status']}, not active")
    return node


def command_done(args: argparse.Namespace, project: Path, root: Path) -> int:
    folder = diagram_dir(project, args.diagram)
    with locked(folder):
        node = require_active(load(folder), args.box, "finish")
    check, ref = node["check"], node["ref"]
    if not ref and node["shape"] != "terminal":
        raise FlowError(
            f"box `{args.box}` isn't tied to code yet. Add `%% code: {args.box} <path>:<symbol>`"
            " and draw again"
        )
    resolved = resolve_ref(root, ref) if ref else None
    # The check can take minutes, so it runs outside the lock and the box is re-checked after.
    result = run_check(check, root, args.timeout) if check else None
    event: dict = {"node": args.box, "note": args.note}
    if result:
        code, tail, seconds = result
        event.update(command=check, exit=code, tail=tail, seconds=seconds)
    failed = bool(result) and result[0] != 0
    if failed:
        event["type"] = "failed"
    else:
        event.update(type="done", resolved=resolved)
    with locked(folder):
        require_active(load(folder), args.box, "finish")
        diagram = append(folder, event)
        diagram = refresh_base(folder, root) or diagram
    if failed:
        lines = [f"{args.box}: failed", f"Check `{check}` exited {code}. Output tail:\n{tail}"]
        report(folder, diagram, *lines)
        return 2
    report(folder, diagram, f"{args.box}: built ({'verified' if result else 'claimed'})")
    return 0


def command_fail(args: argparse.Namespace, project: Path, root: Path) -> None:
    folder = diagram_dir(project, args.diagram)
    with locked(folder):
        require_active(load(folder), args.box, "fail")
        diagram = append(folder, {"type": "failed", "node": args.box, "note": args.note})
    report(folder, diagram, f"{args.box}: failed")


def command_note(args: argparse.Namespace, project: Path, root: Path) -> None:
    folder = diagram_dir(project, args.diagram)
    with locked(folder):
        find_node(load(folder), args.box)
        diagram = append(folder, {"type": "note", "node": args.box, "text": args.text})
    report(folder, diagram, f"{args.box}: noted")


def command_confirm(args: argparse.Namespace, project: Path, root: Path) -> None:
    """Accept changed code. Boxes pointing at the same code are the same judgment, so all clear."""
    folder = diagram_dir(project, args.diagram)
    with locked(folder):
        diagram = load(folder)
        node = find_node(diagram, args.box)
        if not node["stale"] and not node["broken"]:
            raise FlowError(f"box `{args.box}` already matches the code")
        resolved = resolve_ref(root, node["ref"])
        boxes = [
            item["id"]
            for item in diagram["nodes"]
            if item["ref"] == node["ref"] and (item["stale"] or item["broken"])
        ]
        for box in boxes:
            event = {"type": "confirmed", "node": box, "resolved": resolved, "note": args.note}
            diagram = append(folder, event)
        diagram = refresh_base(folder, root) or diagram
    report(folder, diagram, f"Confirmed: {', '.join(boxes)}")


def command_compare(args: argparse.Namespace, project: Path, root: Path) -> None:
    """Record which boxes differ from each commit, so the page can offer them as a choice."""
    commits = []
    for name in args.commits:
        found = git(root, "rev-parse", "--verify", "--quiet", f"{name}^{{commit}}")
        if found.returncode != 0:
            raise FlowError(f"`{name}` isn't a commit in {root}")
        commits.append(found.stdout.strip())
    folders = [diagram_dir(project, args.diagram)] if args.diagram else diagram_dirs(project)
    for folder in folders:
        with locked(folder):
            for commit in commits:
                event = build_comparison(root, commit, load(folder))
                diagram = append(folder, event)
                count = len(event["states"])
                print(f"{folder.name}: {count} boxes differ from {commit[:7]} ({event['subject']})")
        line = push_line(folder, diagram)
        if line:
            print(line)


def command_source(args: argparse.Namespace, project: Path, root: Path) -> None:
    print((diagram_dir(project, args.diagram) / "source.mmd").read_text(), end="")


def command_show(args: argparse.Namespace, project: Path, root: Path) -> int:
    """Compare every chart with the code and report. Exit 2 when a chart no longer matches."""
    url = read_json(project / "project.json", {}).get("url")
    if url:
        print(f"Live view: {url}")
    folders = [diagram_dir(project, args.diagram)] if args.diagram else diagram_dirs(project)
    if not folders:
        print("No diagrams yet. Create one with `flow.py draw <name> < diagram.mmd`.")
        return 0
    drifted = False
    waiting = []
    for folder in folders:
        with locked(folder):
            diagram = scan(folder, root)
            diagram = refresh_base(folder, root) or diagram
        nodes = diagram["nodes"]
        counts = [
            f"{sum(node['status'] == status for node in nodes)} {status}"
            for status in ("planned", "active", "failed")
            if any(node["status"] == status for node in nodes)
        ]
        detail = ", ".join([f"{len(nodes)} boxes", *counts])
        print(f"{diagram['id']}: {diagram['title']} ({detail})")
        for node in nodes:
            if args.diagram:
                marks = [node["shape"]] if node["shape"] != "box" else []
                mark = f" <{', '.join(marks)}>" if marks else ""
                working = node["status"] == "active" and node["agent"]
                agent = f" [{node['agent']}]" if working else ""
                ref = f" {node['ref']}" if node["ref"] else ""
                print(f"  {GLYPHS[node['status']]} {node['id']}{mark}{agent}: {node['title']}{ref}")
            state = "stale" if node["stale"] else "broken" if node["broken"] else None
            if state:
                drifted = True
                print(f"  {diagram['id']}/{node['id']}: {state} ({node['ref']})")
        if diagram["unmapped"]:
            print(f"  Edits outside the chart: {', '.join(diagram['unmapped'])}")
        line = push_line(folder, diagram)
        if line:
            waiting.append(line)
    if not drifted:
        print("Every box matches the code.")
    for line in waiting:
        print(line)
    return 2 if drifted else 0


def command_pushed(args: argparse.Namespace, project: Path, root: Path) -> None:
    folder = diagram_dir(project, args.diagram)
    record_push(folder, args.seq, args.version)
    print(f"Pushed {args.diagram} seq {args.seq}, document version {args.version}.")
    line = push_line(folder, load(folder))
    if line:
        print(line)


def command_watch(args: argparse.Namespace, project: Path, root: Path) -> None:
    """Print one line whenever a change waits to be pushed. Made for the Monitor tool."""
    announced: dict[str, int] = {}
    seen_active = False
    while True:
        settled = True
        for folder in diagram_dirs(project):
            diagram = load(folder)
            pushed = push_state(folder)["seq"]
            active = any(node["status"] == "active" for node in diagram["nodes"])
            seen_active = seen_active or active
            settled = settled and not active and pushed >= diagram["seq"]
            last = diagram["lastTransitionSeq"]
            if last > pushed and last > announced.get(folder.name, 0):
                announced[folder.name] = last
                print(f"{diagram['events'][-1]['text']}. {push_line(folder, diagram)}", flush=True)
        if seen_active and settled:
            print("Nothing is active and every change is pushed.", flush=True)
            return
        time.sleep(WATCH_POLL_SECONDS)


# Hooks


def record_artifact_push(payload: dict) -> bool:
    """Record a successful snapshot push. True when this call was one."""
    raw = payload.get("tool_input", {}).get("file_path")
    if not raw:
        return False
    path = Path(raw)
    if path.parent.name != "snapshots" or not path.is_relative_to(state_home()):
        return False
    response = json.dumps(payload.get("tool_response"))
    found = re.search(r"now at version (\d+)", response)
    if not found:
        raise FlowError(
            f"pushed {path}, but the tool response names no version: {response[:300]}. "
            "Run `flow.py pushed <diagram> --seq <seq> --version <version>`."
        )
    record_push(path.parent.parent, int(path.stem), int(found.group(1)))
    return True


def covers(node: dict, file: str) -> bool:
    if not node["ref"]:
        return False
    path = split_ref(node["ref"])[0].rstrip("/")
    return file == path or file.startswith(path + "/")


def record_edit(folder: Path, root: Path, file: str) -> str | None:
    """Tie an edit to the boxes it touched. Returns a note when no box on this chart covers it."""
    with locked(folder):
        diagram = load(folder)
        matched = {node["id"] for node in diagram["nodes"] if covers(node, file)}
        active = any(node["status"] == "active" for node in diagram["nodes"])
        if matched:
            append(folder, {"type": "edit", "file": file, "nodes": sorted(matched)})
            scan(folder, root, matched)
            refresh_base(folder, root)
        elif active:
            append(folder, {"type": "edit", "file": file, "nodes": []})
            refresh_base(folder, root)
            if file not in diagram["unmapped"]:
                chart = diagram["id"]
                return f"{file} changed and no box in `{chart}` covers it. Add one if it belongs."
    return None


def chart_problems(folders: list[Path]) -> list[str]:
    """Boxes whose code moved. Fixing the chart is the agent's job, so it is told what to fix."""
    problems = []
    for folder in folders:
        diagram = load(folder)
        for node in diagram["nodes"]:
            if node["broken"]:
                problems.append(f"{diagram['id']}/{node['id']}: {node['ref']} no longer exists")
            elif node["stale"]:
                problems.append(f"{diagram['id']}/{node['id']}: {node['ref']} was edited")
    return problems


def fix_instructions(problems: list[str]) -> str:
    return (
        "Live flowchart is out of date. Reread this code and fix the chart now: draw the corrected "
        "Mermaid, or run `flow.py confirm <diagram> <box>` if the box is still right. "
        + "; ".join(problems)
    )


def hook_post_tool(payload: dict) -> None:
    if payload.get("tool_name") == "ArtifactData" and record_artifact_push(payload):
        return
    root = project_root(Path(payload.get("cwd") or os.getcwd()))
    folders = diagram_dirs(project_dir(root))
    messages = []
    if payload.get("tool_name") in EDIT_TOOLS:
        tool_input = payload.get("tool_input", {})
        raw = tool_input.get("file_path") or tool_input.get("notebook_path")
        path = Path(raw).resolve() if raw else None
        if path and path.is_relative_to(root):
            for folder in folders:
                note = record_edit(folder, root, str(path.relative_to(root)))
                if note:
                    messages.append(note)
    if payload.get("tool_name") == "Bash":
        scan_all(folders, root)
    if payload.get("agent_id"):
        return
    problems = chart_problems(folders)
    if problems:
        messages.append(fix_instructions(problems))
    for folder in folders:
        diagram = load(folder)
        if diagram["lastTransitionSeq"] > push_state(folder)["seq"]:
            messages.append(f"Live flowchart is behind. {push_line(folder, diagram)}")
    if messages:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": " ".join(messages),
            }
        }
        print(json.dumps(output))


def hook_stop(payload: dict) -> None:
    if payload.get("stop_hook_active"):
        return
    project = project_dir(project_root(Path(payload.get("cwd") or os.getcwd())))
    folders = diagram_dirs(project)
    problems = chart_problems(folders)
    reasons = [fix_instructions(problems)] if problems else []
    waiting = [line for folder in folders if (line := push_line(folder, load(folder)))]
    if waiting:
        reasons.append("Live flowchart is behind. " + " ".join(waiting))
    if reasons:
        print(json.dumps({"decision": "block", "reason": " ".join(reasons)}))


def command_hook(args: argparse.Namespace) -> None:
    payload = json.loads(sys.stdin.read())
    {"post-tool": hook_post_tool, "stop": hook_stop}[args.event](payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Keep live flowcharts honest against the code.")
    parser.add_argument("--project", type=Path, help="Project folder, if not the current one")
    commands = parser.add_subparsers(dest="command", required=True)

    def add(name: str, handler, help_text: str, box: bool = False, note: bool = False):
        sub = commands.add_parser(name, help=help_text)
        sub.set_defaults(handler=handler)
        if box:
            sub.add_argument("diagram")
            sub.add_argument("box")
        if note:
            sub.add_argument("--note", help="Why, in one line. Shown on the box")
        return sub

    draw = add("draw", command_draw, "Create or update a diagram from Mermaid on stdin")
    draw.add_argument("diagram")
    add("link", command_link, "Record the published artifact URL").add_argument("url")
    add("topic", command_topic, "Name what the project is about").add_argument("text")
    add("show", command_show, "Check charts against the code and report").add_argument(
        "diagram", nargs="?"
    )
    add("source", command_source, "Print a diagram's Mermaid").add_argument("diagram")
    begin = add("begin", command_begin, "Start building or changing a box", box=True, note=True)
    begin.add_argument("--agent", help="Who is working on it")
    done = add("done", command_done, "Finish a box, checking it exists", box=True, note=True)
    done.add_argument("--timeout", type=int, default=CHECK_TIMEOUT_SECONDS, help="Check seconds")
    add("fail", command_fail, "Mark an active box failed", box=True, note=True)
    add("note", command_note, "Attach a note to a box", box=True).add_argument("text")
    add("confirm", command_confirm, "Accept a box's changed code", box=True, note=True)
    compare = add("compare", command_compare, "Mark the boxes that differ from commits")
    compare.add_argument("commits", nargs="+")
    compare.add_argument("--diagram", help="One diagram, if not all of them")
    pushed = add("pushed", command_pushed, "Record a push the hook did not record")
    pushed.add_argument("diagram")
    pushed.add_argument("--seq", type=int, required=True)
    pushed.add_argument("--version", type=int, required=True)
    add("watch", command_watch, "Print a line when a change waits to be pushed")
    hook = add("hook", None, "Entry point for Claude Code hooks")
    hook.add_argument("event", choices=["post-tool", "stop"])
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "hook":
            command_hook(args)
            return 0
        root = project_root((args.project or Path.cwd()).resolve())
        return args.handler(args, project_dir(root), root) or 0
    except FlowError as error:
        print(f"flow.py: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
