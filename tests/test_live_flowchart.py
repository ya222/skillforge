"""The live-flowchart CLI, driven as a real process against real git repositories."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

FLOW = Path(__file__).parent.parent / "skills" / "live-flowchart" / "scripts" / "flow.py"
URL = "https://claude.ai/artifact/abc123"

SESSION_PY = """\
def revoke_session(token):
    store.delete(token)
    return True


def other():
    return 1
"""
SCHEMA_SQL = "CREATE TABLE sessions (\n  id TEXT\n);\n"
DIAGRAM = """\
---
title: POST /logout
---
flowchart TD
  req([POST /logout]) --> valid{Valid session?}
  valid -->|no| deny([401])
  valid -->|yes| revoke["revoke_session()"]
  subgraph store [Session store]
    revoke --> sessions[(sessions)]
  end
  revoke --> email[/Send email/]
  %% code: valid src/session.py:revoke_session
  %% code: revoke src/session.py:revoke_session
  %% code: sessions src/schema.sql:sessions
  %% code: email src/mail.py:send
  class email planned
"""
CHANGED = SESSION_PY.replace("store.delete(token)", "store.expire(token)")


class Flow:
    def __init__(self, root: Path, state: Path) -> None:
        self.root = root
        self.state = state

    def env(self) -> dict[str, str]:
        return {**os.environ, "XDG_STATE_HOME": str(self.state)}

    def run(self, *args: str, stdin: str = "") -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(FLOW), *args],
            cwd=self.root,
            env=self.env(),
            input=stdin,
            capture_output=True,
            text=True,
        )

    def ok(self, *args: str, stdin: str = "") -> str:
        result = self.run(*args, stdin=stdin)
        assert result.returncode == 0, result.stderr
        return result.stdout

    def refused(self, *args: str, stdin: str = "") -> str:
        result = self.run(*args, stdin=stdin)
        assert result.returncode == 1, result.stdout
        return result.stderr

    def draw(self, source: str = DIAGRAM, name: str = "logout") -> str:
        output = self.ok("draw", name, stdin=source)
        self.ok("link", URL)
        return output

    def folder(self, name: str = "logout") -> Path:
        projects = [item for item in (self.state / "sf-live-flowchart").iterdir() if item.is_dir()]
        assert len(projects) == 1
        return projects[0] / "diagrams" / name

    def snapshot(self, name: str = "logout") -> dict:
        snapshots = (self.folder(name) / "snapshots").glob("*.json")
        return json.loads(max(snapshots, key=lambda item: int(item.stem)).read_text())

    def node(self, box: str, name: str = "logout") -> dict:
        return next(item for item in self.snapshot(name)["nodes"] if item["id"] == box)

    def hook(self, event: str, **payload) -> str:
        return self.ok("hook", event, stdin=json.dumps({"cwd": str(self.root), **payload}))

    def edit(self, relative: str, **payload) -> str:
        path = str(self.root / relative)
        return self.hook("post-tool", tool_name="Edit", tool_input={"file_path": path}, **payload)

    def push(self, version: int, name: str = "logout") -> None:
        path = self.folder(name) / "snapshots" / f"{self.snapshot(name)['seq']}.json"
        self.hook(
            "post-tool",
            tool_name="ArtifactData",
            tool_input={"file_path": str(path)},
            tool_response={
                "written": {"url": URL},
                "owned": True,
                "db_write": {"op": "set", "committed": True, "version": version},
            },
        )


@pytest.fixture
def flow(tmp_path: Path) -> Flow:
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    (root / "src" / "session.py").write_text(SESSION_PY)
    (root / "src" / "schema.sql").write_text(SCHEMA_SQL)
    return Flow(root, tmp_path / "state")


def test_a_chart_describes_the_code_with_a_shape_for_each_kind_of_thing(flow: Flow) -> None:
    flow.draw()
    snapshot = flow.snapshot()
    shapes = {node["id"]: node["shape"] for node in snapshot["nodes"]}
    assert shapes == {
        "req": "terminal",
        "valid": "decision",
        "deny": "terminal",
        "revoke": "box",
        "sessions": "table",
        "email": "io",
    }
    assert snapshot["title"] == "POST /logout"
    assert snapshot["root"] == str(flow.root.resolve())
    assert snapshot["groups"] == [{"id": "store", "title": "Session store", "parent": None}]
    assert flow.node("sessions")["group"] == "store"
    assert flow.node("revoke")["status"] == "built"
    assert flow.node("revoke")["resolved"]["line"] == 1
    assert flow.node("sessions")["resolved"]["line"] == 1
    assert flow.node("email")["status"] == "planned"
    labels = {(edge["from"], edge["to"]): edge["label"] for edge in snapshot["edges"]}
    assert labels[("valid", "revoke")] == "yes"


def box(ref: str = "src/session.py:revoke_session", shape: str = "a[A]", extra: str = "") -> str:
    return f"---\ntitle: T\n---\nflowchart TD\n  {shape} --> z([End])\n  %% code: a {ref}\n{extra}"


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("flowchart TD\n  a([A])\n", "frontmatter with a title"),
        ("---\ntitle: T\n---\nflowchart LR\n  a([A])\n", "top to bottom"),
        ("---\ntitle: T\n---\nflowchart TD\n  a([A]) --> b\n", "`b` has no shape"),
        ("---\ntitle: T\n---\nflowchart TD\n  a(A)\n", "unsupported shape"),
        ("---\ntitle: T\n---\nflowchart TD\n  a([A])\n  a([B])\n", "declared twice"),
        ("---\ntitle: T\n---\nflowchart TD\n  a([A])\n  b([B])\n", "no arrows: a, b"),
        ("---\ntitle: T\n---\nflowchart TD\n  style a fill:#f00\n", "isn't supported"),
        (box(extra="  class a done\n"), "only `class <ids> planned`"),
        (box(ref="src/missing.py:x"), "doesn't exist"),
        (box(ref="src/session.py:nothing"), "doesn't appear"),
        (box(ref="src/session.py:12"), "not a line number"),
        (box(ref="../outside.py"), "outside the project"),
        ("---\ntitle: T\n---\nflowchart TD\n  a[A] --> z([End])\n", "isn't tied to code"),
        (box(shape="a{A}"), "at least two exits"),
        (box(shape="a[(A)]", ref="src/schema.sql"), "real database table"),
    ],
)
def test_charts_the_code_cant_back_up_are_refused(flow: Flow, source: str, message: str) -> None:
    assert message in flow.refused("draw", "bad", stdin=source)


def test_refs_find_the_definition_with_the_exact_name(flow: Flow) -> None:
    code = "class Build:\n    pass\n\n\nx = build\n\n\ndef build():\n    return 1\n"
    (flow.root / "src" / "render.py").write_text(code)
    flow.draw(box(ref="src/render.py:build"), "exact")
    assert flow.node("a", "exact")["resolved"]["line"] == 8


def test_one_cylinder_per_table(flow: Flow) -> None:
    source = (
        "---\ntitle: T\n---\nflowchart TD\n  a[(A)] --> b[(B)]\n"
        "  %% code: a src/schema.sql:sessions\n  %% code: b src/schema.sql:sessions\n"
    )
    assert "one cylinder per table" in flow.refused("draw", "bad", stdin=source)


def test_diagrams_may_loop_like_real_control_flow(flow: Flow) -> None:
    source = (
        "---\ntitle: Retry\n---\nflowchart TD\n  a([Start]) --> b[Try]\n  b --> c{OK?}\n"
        "  c -->|no| b\n  c -->|yes| d([End])\n"
        "  %% code: b src/session.py:revoke_session\n  %% code: c src/session.py:revoke_session\n"
    )
    flow.draw(source, "retry")
    assert len(flow.snapshot("retry")["edges"]) == 4


def test_a_planned_box_becomes_built_only_once_its_code_exists(flow: Flow) -> None:
    flow.draw()
    flow.ok("begin", "logout", "email", "--agent", "worker")
    assert "doesn't exist" in flow.refused("done", "logout", "email")
    assert flow.node("email")["status"] == "active"

    (flow.root / "src" / "mail.py").write_text("def send():\n    pass\n")
    assert "claimed" in flow.ok("done", "logout", "email")
    node = flow.node("email")
    assert (node["status"], node["result"], node["changed"]) == ("built", "claimed", True)


def test_redrawing_cannot_skip_the_work_on_a_planned_box(flow: Flow) -> None:
    flow.draw()
    (flow.root / "src" / "mail.py").write_text("def send():\n    pass\n")
    flow.draw(DIAGRAM.replace("  class email planned\n", ""))
    assert flow.node("email")["status"] == "planned"


def test_checks_decide_whether_a_box_is_verified(flow: Flow) -> None:
    flow.draw(DIAGRAM.replace("  class email", "  %% check: revoke test -f ok\n  class email"))
    flow.ok("begin", "logout", "revoke")
    failed = flow.run("done", "logout", "revoke")
    assert failed.returncode == 2
    assert flow.node("revoke")["status"] == "failed"

    (flow.root / "ok").touch()
    flow.ok("begin", "logout", "revoke")
    assert "verified" in flow.ok("done", "logout", "revoke")
    node = flow.node("revoke")
    assert (node["result"], node["attempts"], node["checkResult"]["exit"]) == ("verified", 2, 0)


def test_changing_code_behind_a_box_marks_it_stale_until_confirmed(flow: Flow) -> None:
    flow.draw()
    assert "Every box matches" in flow.ok("show")

    path = flow.root / "src" / "session.py"
    path.write_text(SESSION_PY.replace("return 1", "return 2"))
    assert "Every box matches" in flow.ok("show"), "only the block behind the box counts"

    path.write_text(CHANGED)
    result = flow.run("show")
    assert result.returncode == 2
    assert "logout/revoke: stale" in result.stdout
    assert flow.node("revoke")["stale"]

    flow.ok("confirm", "logout", "revoke", "--note", "Same flow, new call")
    assert not flow.node("revoke")["stale"]
    assert "already matches" in flow.refused("confirm", "logout", "revoke")


def test_confirming_clears_every_box_on_the_same_code(flow: Flow) -> None:
    flow.draw()
    (flow.root / "src" / "session.py").write_text(CHANGED)
    flow.run("show")
    assert flow.node("valid")["stale"]
    assert flow.node("revoke")["stale"]
    assert "Confirmed: valid, revoke" in flow.ok("confirm", "logout", "revoke", "--note", "Fine")
    assert not flow.node("valid")["stale"]
    assert not flow.node("revoke")["stale"]


def test_a_branch_can_point_at_its_own_condition(flow: Flow) -> None:
    code = "def handle(x):\n    if x:\n        one()\n    if not x:\n        two()\n"
    (flow.root / "src" / "branch.py").write_text(code)
    source = (
        "---\ntitle: T\n---\nflowchart TD\n"
        "  a{First?} -->|yes| b([Y])\n  a -->|no| c{Second?}\n"
        "  c -->|yes| d([Y2])\n  c -->|no| e([N])\n"
        "  %% code: a src/branch.py:handle > if x:\n"
        "  %% code: c src/branch.py:handle > if not x:\n"
    )
    flow.draw(source, "branch")
    assert flow.node("a", "branch")["resolved"]["line"] == 2
    assert flow.node("c", "branch")["resolved"]["line"] == 4

    (flow.root / "src" / "branch.py").write_text(code.replace("two()", "three()"))
    assert flow.run("show").returncode == 2
    assert flow.node("c", "branch")["stale"]
    assert not flow.node("a", "branch")["stale"]

    assert "doesn't appear in `handle`" in flow.refused(
        "draw", "bad", stdin=source.replace("if not x:", "if never:")
    )


def test_removing_the_next_function_does_not_flag_this_one(flow: Flow) -> None:
    flow.draw()
    path = flow.root / "src" / "session.py"
    path.write_text(SESSION_PY[: SESSION_PY.index("def other")].rstrip() + "\n")
    assert "Every box matches" in flow.ok("show")


def test_reverting_the_code_clears_stale(flow: Flow) -> None:
    flow.draw()
    path = flow.root / "src" / "session.py"
    path.write_text(CHANGED)
    flow.run("show")
    path.write_text(SESSION_PY)
    assert "Every box matches" in flow.ok("show")
    assert not flow.node("revoke")["stale"]


def test_removing_the_code_breaks_the_box(flow: Flow) -> None:
    flow.draw()
    (flow.root / "src" / "session.py").write_text("x = 1\n")
    result = flow.run("show")
    assert result.returncode == 2
    assert "logout/revoke: broken" in result.stdout


def test_a_box_being_worked_on_is_expected_to_change(flow: Flow) -> None:
    flow.draw()
    flow.ok("begin", "logout", "revoke")
    (flow.root / "src" / "session.py").write_text(CHANGED)
    flow.ok("done", "logout", "revoke")
    assert "logout/valid: stale" in flow.run("show").stdout
    assert not flow.node("revoke")["stale"]


def test_redrawing_keeps_progress_and_accepts_the_code_as_it_is(flow: Flow) -> None:
    flow.draw()
    flow.ok("begin", "logout", "revoke", "--agent", "worker")
    flow.draw(DIAGRAM.replace("Valid session?", "Session valid?"))
    assert flow.node("valid")["title"] == "Session valid?"
    assert flow.node("revoke")["status"] == "active"
    assert flow.node("revoke")["agent"] == "worker"
    source = DIAGRAM.replace("class email planned", "class email,revoke planned")
    assert "can't go back" in flow.refused("draw", "logout", stdin=source)


def commit(flow: Flow, message: str) -> str:
    identity = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    subprocess.run(["git", "add", "-A"], cwd=flow.root, check=True)
    subprocess.run(["git", *identity, "commit", "-qm", message], cwd=flow.root, check=True)
    head = ["git", "rev-parse", "HEAD"]
    return subprocess.run(head, cwd=flow.root, capture_output=True, text=True).stdout.strip()


def test_compare_marks_boxes_added_or_changed_since_a_commit(flow: Flow) -> None:
    first = commit(flow, "First")
    (flow.root / "src" / "session.py").write_text(CHANGED + "\n\ndef added_later():\n    pass\n")
    (flow.root / "src" / "mail.py").write_text("def send():\n    pass\n")
    source = DIAGRAM.replace("  class email planned\n", "") + (
        "  revoke --> later[New]\n  %% code: later src/session.py:added_later\n"
    )
    flow.draw(source)
    output = flow.ok("compare", "HEAD")
    assert "boxes differ from" in output
    entry = flow.snapshot()["comparisons"][0]
    assert entry["commit"] == first
    assert entry["subject"] == "First"
    assert entry["states"] == {
        "valid": "changed",
        "revoke": "changed",
        "email": "added",
        "later": "added",
    }

    second = commit(flow, "Second")
    flow.ok("compare", "HEAD", first)
    comparisons = flow.snapshot()["comparisons"]
    assert [item["commit"] for item in comparisons] == [first, second]
    assert comparisons[1]["states"] == {}
    assert "isn't a commit" in flow.refused("compare", "nonsense")


def test_comparing_shows_the_diff_other_files_and_removed_boxes(flow: Flow) -> None:
    first = commit(flow, "First")
    flow.draw()
    assert flow.snapshot()["comparisons"][0]["auto"]
    (flow.root / "src" / "session.py").write_text(CHANGED)
    (flow.root / "notes.txt").write_text("new")
    flow.draw(
        DIAGRAM.replace("  revoke --> email[/Send email/]\n", "").replace(
            "  %% code: email src/mail.py:send\n  class email planned\n", ""
        )
    )
    entry = flow.snapshot()["comparisons"][0]
    assert entry["commit"] == first
    assert entry["auto"]
    assert set(entry["states"]) == {"valid", "revoke"}
    assert "-    store.delete(token)" in entry["diffs"]["revoke"]
    assert "+    store.expire(token)" in entry["diffs"]["revoke"]
    assert {"path": "notes.txt", "status": "A"} in entry["files"]
    assert entry["filesTotal"] == 1
    assert entry["removed"] == [{"id": "email", "title": "Send email"}]


def test_the_branch_comparison_stays_current_without_being_asked(flow: Flow) -> None:
    commit(flow, "First")
    subprocess.run(["git", "branch", "-M", "main"], cwd=flow.root, check=True)
    subprocess.run(["git", "checkout", "-qb", "work"], cwd=flow.root, check=True)
    (flow.root / "src" / "session.py").write_text(CHANGED)
    commit(flow, "On the branch")
    flow.draw()
    fork = subprocess.run(
        ["git", "rev-parse", "main"], cwd=flow.root, capture_output=True, text=True
    ).stdout.strip()
    entry = flow.snapshot()["comparisons"][0]
    assert (entry["commit"], entry["auto"]) == (fork, True)
    assert set(entry["states"]) == {"valid", "revoke"}

    (flow.root / "src" / "session.py").write_text(SESSION_PY)
    flow.hook("post-tool", tool_name="Bash", tool_input={})
    assert flow.snapshot()["comparisons"][0]["states"] == {}
    seq = flow.snapshot()["seq"]
    flow.hook("post-tool", tool_name="Bash", tool_input={})
    assert flow.snapshot()["seq"] == seq


def test_a_comparison_alone_does_not_nag_the_agent(flow: Flow) -> None:
    commit(flow, "First")
    flow.draw()
    flow.push(1)
    (flow.root / "notes.txt").write_text("new")
    assert flow.hook("post-tool", tool_name="Bash", tool_input={}) == ""


def test_older_comparison_records_still_replay(flow: Flow) -> None:
    flow.draw()
    log = flow.folder() / "events.jsonl"
    old = {
        "seq": 2,
        "at": "2026-01-01T00:00:00Z",
        "type": "compared",
        "commit": "abc1234def",
        "short": "abc1234",
        "subject": "Old",
        "states": {"revoke": "changed"},
    }
    log.write_text(log.read_text() + json.dumps(old) + "\n")
    flow.ok("note", "logout", "revoke", "Next")
    entry = flow.snapshot()["comparisons"][0]
    assert (entry["auto"], entry["diffs"], entry["files"]) == (False, {}, [])


def test_a_chart_keeps_its_branch_and_the_project_keeps_its_topic(flow: Flow) -> None:
    commit(flow, "First")
    subprocess.run(["git", "checkout", "-qb", "feature/invites"], cwd=flow.root, check=True)
    flow.ok("topic", "Team invites")
    flow.draw()
    assert (flow.snapshot()["branch"], flow.snapshot()["topic"]) == (
        "feature/invites",
        "Team invites",
    )
    subprocess.run(["git", "checkout", "-qb", "next"], cwd=flow.root, check=True)
    flow.ok("note", "logout", "revoke", "Moved branch")
    assert flow.snapshot()["branch"] == "feature/invites"


MULTILINE = """\
async def run_import(
    session,
    *,
    start,
) -> list:
    documents = []
    if isinstance(session, Stats):
        documents.append(start)
    return documents


def other():
    return 1
"""


def multiline_chart(ref: str) -> str:
    return (
        "---\ntitle: T\n---\nflowchart TD\n  a[Run] --> z([End])\n"
        f"  %% code: a src/runner.py:{ref}\n"
    )


def test_a_box_covers_the_body_after_a_multi_line_signature(flow: Flow) -> None:
    path = flow.root / "src" / "runner.py"
    path.write_text(MULTILINE)
    flow.draw(multiline_chart("run_import"), "runner")
    assert "Every box matches" in flow.ok("show")
    path.write_text(MULTILINE.replace("return 1", "return 2"))
    assert "Every box matches" in flow.ok("show")
    path.write_text(MULTILINE.replace("documents = []", "documents = [1]"))
    assert flow.run("show").returncode == 2
    assert flow.node("a", "runner")["stale"]


def test_a_branch_can_point_at_a_line_after_a_multi_line_signature(flow: Flow) -> None:
    (flow.root / "src" / "runner.py").write_text(MULTILINE)
    flow.draw(multiline_chart("run_import > isinstance(session, Stats)"), "runner")
    assert flow.node("a", "runner")["resolved"]["line"] == 7


def test_multi_line_signatures_work_with_braces_too(flow: Flow) -> None:
    code = "export function run(\n  a,\n  b,\n) {\n  return a;\n}\n\nconst next = 1;\n"
    path = flow.root / "src" / "runner.ts"
    path.write_text(code)
    source = multiline_chart("run").replace("runner.py", "runner.ts")
    flow.draw(source, "runner")
    path.write_text(code.replace("next = 1", "next = 2"))
    assert "Every box matches" in flow.ok("show")
    path.write_text(code.replace("return a", "return b"))
    assert flow.run("show").returncode == 2


def on_other_branch(flow: Flow) -> None:
    commit(flow, "First")
    subprocess.run(["git", "branch", "-M", "main"], cwd=flow.root, check=True)
    subprocess.run(["git", "checkout", "-qb", "m2"], cwd=flow.root, check=True)
    (flow.root / "src" / "mail.py").write_text("def send():\n    pass\n")
    commit(flow, "On m2")
    subprocess.run(["git", "checkout", "-q", "main"], cwd=flow.root, check=True)


def current(flow: Flow) -> str:
    found = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    return subprocess.run(found, cwd=flow.root, capture_output=True, text=True).stdout.strip()


def test_draw_can_read_another_branch_without_switching(flow: Flow) -> None:
    on_other_branch(flow)
    source = DIAGRAM.replace("  class email planned\n", "")
    assert "src/mail.py doesn't exist" in flow.refused("draw", "logout", stdin=source)
    flow.ok("draw", "logout", "--ref", "m2", stdin=source)
    flow.ok("link", URL)
    assert current(flow) == "main"
    assert flow.snapshot()["branch"] == "m2"
    assert flow.node("email")["resolved"]["line"] == 1
    assert flow.snapshot()["comparisons"][0]["states"] == {"email": "added"}
    assert "isn't a branch" in flow.refused("draw", "x", "--ref", "nope", stdin=source)


def test_switching_branches_does_not_flag_a_chart(flow: Flow) -> None:
    on_other_branch(flow)
    source = DIAGRAM.replace("  class email planned\n", "")
    flow.ok("draw", "logout", "--ref", "m2", stdin=source)
    flow.ok("link", URL)
    assert "Every box matches" in flow.ok("show")
    subprocess.run(["git", "checkout", "-q", "m2"], cwd=flow.root, check=True)
    assert "Every box matches" in flow.ok("show")
    subprocess.run(["git", "checkout", "-q", "main"], cwd=flow.root, check=True)
    assert "Every box matches" in flow.ok("show")

    (flow.root / "src" / "session.py").write_text(CHANGED)
    flow.edit("src/session.py")
    assert not flow.node("revoke")["stale"]
    assert flow.node("revoke")["touched"] == []
    assert "Switch to it to build" in flow.refused("begin", "logout", "revoke")


def test_a_chart_on_another_branch_notices_when_that_branch_moves(flow: Flow) -> None:
    on_other_branch(flow)
    source = DIAGRAM.replace("  class email planned\n", "")
    flow.ok("draw", "logout", "--ref", "m2", stdin=source)
    flow.ok("link", URL)
    subprocess.run(["git", "checkout", "-q", "m2"], cwd=flow.root, check=True)
    (flow.root / "src" / "mail.py").write_text("def send():\n    return 1\n")
    commit(flow, "Move m2")
    subprocess.run(["git", "checkout", "-q", "main"], cwd=flow.root, check=True)
    assert flow.run("show").returncode == 2
    assert flow.node("email")["stale"]


def test_reminders_are_said_once(flow: Flow) -> None:
    flow.ok("draw", "logout", stdin=DIAGRAM)
    assert flow.hook("post-tool", tool_name="Bash", tool_input={}) == "", "nothing to push to yet"
    flow.ok("link", URL)
    flow.push(1)
    flow.ok("begin", "logout", "revoke")
    assert "PUSH" in flow.hook("post-tool", tool_name="Bash", tool_input={})
    assert flow.hook("post-tool", tool_name="Bash", tool_input={}) == ""
    assert "PUSH" in json.loads(flow.hook("stop"))["reason"], "the Stop hook still catches it"


def test_show_summarizes_unless_asked_for_one_chart(flow: Flow) -> None:
    flow.draw()
    summary = flow.ok("show")
    assert "logout: POST /logout (6 boxes, 1 planned)" in summary
    assert "revoke" not in summary
    assert "[=] revoke: revoke_session()" in flow.ok("show", "logout")


def test_show_connects_a_session_to_the_page_once_it_exists(flow: Flow) -> None:
    flow.ok("draw", "logout", stdin=DIAGRAM)
    assert "ArtifactComments" not in flow.ok("show")
    flow.ok("link", URL)
    summary = flow.ok("show").splitlines()
    assert f"WATCH: ArtifactComments action=watch url={URL}" in summary
    assert f"READ: ArtifactComments action=read url={URL}" in summary
    assert "ArtifactComments" not in flow.ok("show", "logout")


def test_replay_is_identical(flow: Flow) -> None:
    flow.draw()
    flow.ok("begin", "logout", "revoke", "--note", "Starting")
    flow.ok("note", "logout", "revoke", "A decision")
    replay = (
        "import json, pathlib, runpy, sys; m = runpy.run_path(sys.argv[1]); "
        "print(json.dumps(m['fold'](m['read_events'](pathlib.Path(sys.argv[2])))))"
    )
    replayed = subprocess.run(
        [sys.executable, "-B", "-c", replay, str(FLOW), str(flow.folder())],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(replayed.stdout) == flow.snapshot()


def test_concurrent_writers_lose_nothing(flow: Flow) -> None:
    flow.draw()
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda i: flow.run("note", "logout", "revoke", f"n{i}"), range(40)))
    assert all(result.returncode == 0 for result in results)
    lines = (flow.folder() / "events.jsonl").read_text().splitlines()
    assert [json.loads(line)["seq"] for line in lines] == list(range(1, 42))
    assert {note["text"] for note in flow.node("revoke")["notes"]} == {f"n{i}" for i in range(40)}


def test_the_most_recently_started_box_is_current(flow: Flow) -> None:
    flow.draw()
    flow.ok("begin", "logout", "valid")
    flow.ok("begin", "logout", "revoke")
    assert flow.node("revoke")["current"]
    assert not flow.node("valid")["current"]


def test_first_draw_publishes_and_later_diagrams_share_the_artifact(flow: Flow) -> None:
    output = flow.ok("draw", "logout", stdin=DIAGRAM)
    publish = next(line for line in output.splitlines() if line.startswith("PUBLISH"))
    assert '"comments":{}' in publish
    assert '"path":"diagrams"' in publish
    view = Path(publish.split("file_path=")[1].split()[0])
    assert view.read_bytes() == (FLOW.parent.parent / "assets" / "view.html").read_bytes()
    assert "PUSH blocked" in output

    flow.ok("link", URL)
    second = flow.ok("draw", "second", stdin=DIAGRAM)
    assert "PUBLISH" not in second
    assert f"Live view: {URL}" in second
    assert "doc_id=second" in second


def test_push_lines_track_the_version_for_each_diagram(flow: Flow) -> None:
    flow.draw()
    first = next(line for line in flow.ok("show").splitlines() if line.startswith("PUSH"))
    assert "if_version" not in first
    assert "collection=diagrams" in first
    flow.push(1)
    assert "PUSH" not in flow.ok("show")
    assert "if_version=1" in flow.ok("begin", "logout", "revoke")


def test_hook_reports_a_push_it_cannot_read(flow: Flow) -> None:
    flow.draw()
    body = {
        "cwd": str(flow.root),
        "tool_name": "ArtifactData",
        "tool_input": {"file_path": str(flow.folder() / "snapshots" / "1.json")},
        "tool_response": "unexpected",
    }
    assert "names no version" in flow.refused("hook", "post-tool", stdin=json.dumps(body))


def test_edits_touch_the_boxes_they_belong_to(flow: Flow) -> None:
    flow.draw()
    flow.ok("begin", "logout", "revoke")
    flow.edit("src/session.py")
    assert flow.node("revoke")["touched"] == ["src/session.py"]
    flow.edit("README.md")
    assert flow.snapshot()["unmapped"] == ["README.md"]
    before = flow.snapshot()["seq"]
    flow.edit("../outside.txt")
    assert flow.snapshot()["seq"] == before


def test_an_edit_outside_active_work_flags_the_box_at_once(flow: Flow) -> None:
    flow.draw()
    flow.push(1)
    (flow.root / "src" / "session.py").write_text(CHANGED)
    reminder = json.loads(flow.edit("src/session.py"))
    assert flow.node("revoke")["stale"]
    assert "if_version=1" in reminder["hookSpecificOutput"]["additionalContext"]


def test_a_shell_command_that_changes_code_flags_the_box(flow: Flow) -> None:
    flow.draw()
    flow.push(1)
    (flow.root / "src" / "session.py").write_text(CHANGED)
    reminder = json.loads(flow.hook("post-tool", tool_name="Bash", tool_input={}))
    assert flow.node("revoke")["stale"]
    assert "if_version=1" in reminder["hookSpecificOutput"]["additionalContext"]


def test_post_tool_hook_reminds_the_orchestrator_about_changes_only(flow: Flow) -> None:
    flow.draw()
    flow.push(1)
    assert flow.hook("post-tool", tool_name="Bash", tool_input={}) == ""
    flow.ok("begin", "logout", "revoke")
    assert flow.hook("post-tool", tool_name="Bash", tool_input={}, agent_id="sub") == ""
    reminder = json.loads(flow.hook("post-tool", tool_name="Bash", tool_input={}))
    assert "PUSH" in reminder["hookSpecificOutput"]["additionalContext"]


def test_the_agent_is_told_to_fix_a_chart_that_no_longer_matches(flow: Flow) -> None:
    flow.draw()
    flow.push(1)
    (flow.root / "src" / "session.py").write_text(CHANGED)
    reminder = json.loads(flow.edit("src/session.py"))
    context = reminder["hookSpecificOutput"]["additionalContext"]
    assert "fix the chart now" in context
    assert "logout/revoke: src/session.py:revoke_session was edited" in context

    (flow.root / "src" / "session.py").write_text("x = 1\n")
    context = json.loads(flow.hook("post-tool", tool_name="Bash", tool_input={}))[
        "hookSpecificOutput"
    ]["additionalContext"]
    assert "src/session.py:revoke_session no longer exists" in context


def test_the_agent_cannot_finish_quietly_with_a_stale_chart(flow: Flow) -> None:
    flow.draw()
    flow.push(1)
    (flow.root / "src" / "session.py").write_text(CHANGED)
    flow.run("show")
    flow.push(2)
    assert "fix the chart now" in json.loads(flow.hook("stop"))["reason"]
    assert flow.hook("stop", stop_hook_active=True) == ""

    flow.ok("confirm", "logout", "revoke", "--note", "Still right")
    flow.push(3)
    assert flow.hook("stop") == ""


def test_the_agent_is_told_once_about_a_file_the_chart_does_not_cover(flow: Flow) -> None:
    flow.draw()
    flow.ok("begin", "logout", "revoke")
    first = json.loads(flow.edit("README.md"))["hookSpecificOutput"]["additionalContext"]
    assert "README.md changed and no box in `logout` covers it" in first
    assert flow.edit("README.md") == ""


def test_stop_hook_blocks_once_while_anything_is_unpushed(flow: Flow) -> None:
    assert flow.hook("stop") == ""
    flow.draw()
    assert json.loads(flow.hook("stop"))["decision"] == "block"
    assert flow.hook("stop", stop_hook_active=True) == ""
    flow.push(1)
    assert flow.hook("stop") == ""


def test_draw_installs_the_copy_that_hook_commands_run(flow: Flow) -> None:
    flow.draw()
    installed = flow.state / "sf-live-flowchart" / "flow.py"
    assert installed.read_bytes() == FLOW.read_bytes()
    command = next(
        line.split("command: ", 1)[1]
        for line in (FLOW.parent.parent / "SKILL.md").read_text().splitlines()
        if "hook stop" in line
    )
    blocked = subprocess.run(
        command,
        shell=True,
        cwd=flow.root,
        env=flow.env(),
        input="{}",
        capture_output=True,
        text=True,
    )
    assert blocked.returncode == 0, blocked.stderr
    assert json.loads(blocked.stdout)["decision"] == "block"


def test_watch_announces_changes_and_exits_when_settled(flow: Flow) -> None:
    flow.draw()
    flow.push(1)
    watcher = subprocess.Popen(
        [sys.executable, str(FLOW), "watch"],
        cwd=flow.root,
        env=flow.env(),
        stdout=subprocess.PIPE,
        text=True,
    )
    flow.ok("begin", "logout", "revoke")
    first = watcher.stdout.readline()
    assert first.startswith("revoke started.")
    assert "if_version=1" in first

    flow.ok("done", "logout", "revoke")
    flow.push(2)
    output, _ = watcher.communicate(timeout=10)
    assert output.splitlines()[-1] == "Nothing is active and every change is pushed."
    assert watcher.returncode == 0
