from __future__ import annotations

from scripts import roadmap_harness


TODO_TEXT = """
# TODO

## Roadmap Loop Harness

### Execution Queue

| id | status | title | verify |
| --- | --- | --- | --- |
| LOOP-001 | active | Active Task | pytest -q |
| LOOP-002 | pending | Pending Task | python check.py |
| LOOP-003 | archived | Old Task | docs only |
"""


NEXT_SESSION_TEXT = """
# NEXT

## Session Loop Harness

- current_active_id: `LOOP-001`
- current_active_title: `Active Task`
- session_start_command: `python scripts/roadmap_harness.py status`
- default_regression_gate: `python scripts/check_ops_baseline_gate.py`
- closeout_rule: `done after docs and commit`
- blocked_rule: `record blocker and reopen rule`
- promotion_rule: `promote first pending item`
"""


def test_parse_execution_queue_reads_rows():
    rows = roadmap_harness.parse_execution_queue(TODO_TEXT)

    assert len(rows) == 3
    assert rows[0]["id"] == "LOOP-001"
    assert rows[1]["status"] == "pending"


def test_build_report_requires_exact_active_match():
    report = roadmap_harness.build_report(
        todo_text=TODO_TEXT,
        next_session_text=NEXT_SESSION_TEXT,
        current_branch="main",
    )

    assert report["ready"] is True
    assert report["active_item"]["id"] == "LOOP-001"
    assert report["counts"]["pending"] == 1


def test_build_report_detects_active_mismatch():
    bad_next_session = NEXT_SESSION_TEXT.replace("LOOP-001", "LOOP-999", 1)

    report = roadmap_harness.build_report(
        todo_text=TODO_TEXT,
        next_session_text=bad_next_session,
        current_branch="main",
    )

    assert report["ready"] is False
    assert "current_active_id does not match" in report["errors"][0]


def test_validate_queue_rejects_multiple_active_items():
    bad_todo = TODO_TEXT.replace(
        "| LOOP-002 | pending | Pending Task | python check.py |",
        "| LOOP-002 | active | Pending Task | python check.py |",
    )

    report = roadmap_harness.build_report(
        todo_text=bad_todo,
        next_session_text=NEXT_SESSION_TEXT,
        current_branch="main",
    )

    assert report["ready"] is False
    assert "Expected exactly one active item" in report["errors"][0]


def test_build_report_detects_active_title_mismatch():
    bad_next_session = NEXT_SESSION_TEXT.replace("Active Task", "Wrong Title", 1)

    report = roadmap_harness.build_report(
        todo_text=TODO_TEXT,
        next_session_text=bad_next_session,
        current_branch="main",
    )

    assert report["ready"] is False
    assert "current_active_title does not match" in report["errors"][0]


def test_build_report_warns_on_non_main_branch():
    report = roadmap_harness.build_report(
        todo_text=TODO_TEXT,
        next_session_text=NEXT_SESSION_TEXT,
        current_branch="feature/v1.5-agent-ready-runtime",
    )

    assert report["ready"] is True
    assert report["warnings"]
    assert "Non-main branch detected" in report["warnings"][0]
