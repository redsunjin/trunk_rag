from __future__ import annotations

import argparse
import re
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

DASHBOARD_START = "<!-- ROADMAP_DASHBOARD_START -->"
DASHBOARD_END = "<!-- ROADMAP_DASHBOARD_END -->"

CHECKBOX_DONE_PATTERN = re.compile(r"^- \[x\] ", re.MULTILINE)
CHECKBOX_PENDING_PATTERN = re.compile(r"^- \[ \] ", re.MULTILINE)
IMMEDIATE_DONE_PATTERN = re.compile(r"^- \[x\] `\[Immediate\]` ", re.MULTILINE)
IMMEDIATE_PENDING_PATTERN = re.compile(r"^- \[ \] `\[Immediate\]` ", re.MULTILINE)
CONDITIONAL_DONE_PATTERN = re.compile(r"^- \[x\] `\[Conditional\]` ", re.MULTILINE)
CONDITIONAL_PENDING_PATTERN = re.compile(r"^- \[ \] `\[Conditional\]` ", re.MULTILINE)


def _run_git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _count(pattern: re.Pattern[str], text: str) -> int:
    return len(pattern.findall(text))


def _pct(done: int, total: int) -> str:
    if total <= 0:
        return "0.0%"
    return f"{(done / total) * 100:.1f}%"


def build_dashboard_markdown(
    *,
    now_text: str,
    branch: str,
    head: str,
    worktree: str,
    todo_done: int,
    todo_pending: int,
    immediate_done: int,
    immediate_pending: int,
    conditional_done: int,
    conditional_pending: int,
) -> str:
    todo_total = todo_done + todo_pending
    immediate_total = immediate_done + immediate_pending
    conditional_total = conditional_done + conditional_pending
    return "\n".join(
        [
            DASHBOARD_START,
            "| Metric | Value |",
            "|---|---|",
            f"| Last Updated (KST) | {now_text} |",
            f"| Branch / HEAD | `{branch}` / `{head}` |",
            f"| Working Tree | {worktree} |",
            f"| TODO Progress | {todo_done}/{todo_total} ({_pct(todo_done, todo_total)}) |",
            f"| Immediate Track | {immediate_done}/{immediate_total} ({_pct(immediate_done, immediate_total)}) |",
            f"| Conditional Track | {conditional_done}/{conditional_total} ({_pct(conditional_done, conditional_total)}) |",
            DASHBOARD_END,
        ]
    )


def update_roadmap(roadmap_path: Path, dashboard_md: str) -> None:
    text = roadmap_path.read_text(encoding="utf-8")
    if DASHBOARD_START not in text or DASHBOARD_END not in text:
        raise ValueError(
            f"Dashboard markers not found in {roadmap_path}. "
            f"Expected {DASHBOARD_START} ... {DASHBOARD_END}."
        )

    updated = re.sub(
        rf"{re.escape(DASHBOARD_START)}[\s\S]*?{re.escape(DASHBOARD_END)}",
        dashboard_md,
        text,
        count=1,
    )
    roadmap_path.write_text(updated, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Update roadmap dashboard stats block.")
    parser.add_argument("--roadmap", type=Path, default=Path("NEXT_SESSION_PLAN.md"))
    parser.add_argument("--todo", type=Path, default=Path("TODO.md"))
    parser.add_argument("--timezone", type=str, default="Asia/Seoul")
    args = parser.parse_args()

    cwd = Path.cwd()
    roadmap_path = cwd / args.roadmap
    todo_path = cwd / args.todo

    todo_text = todo_path.read_text(encoding="utf-8")
    roadmap_text = roadmap_path.read_text(encoding="utf-8")

    todo_done = _count(CHECKBOX_DONE_PATTERN, todo_text)
    todo_pending = _count(CHECKBOX_PENDING_PATTERN, todo_text)
    immediate_done = _count(IMMEDIATE_DONE_PATTERN, roadmap_text)
    immediate_pending = _count(IMMEDIATE_PENDING_PATTERN, roadmap_text)
    conditional_done = _count(CONDITIONAL_DONE_PATTERN, roadmap_text)
    conditional_pending = _count(CONDITIONAL_PENDING_PATTERN, roadmap_text)

    now = datetime.now(ZoneInfo(args.timezone))
    now_text = now.strftime("%Y-%m-%d %H:%M:%S")

    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    head = _run_git(["rev-parse", "--short", "HEAD"], cwd=cwd)
    status_short = _run_git(["status", "--short"], cwd=cwd)
    worktree = "clean" if status_short == "" else "dirty"

    dashboard_md = build_dashboard_markdown(
        now_text=now_text,
        branch=branch,
        head=head,
        worktree=worktree,
        todo_done=todo_done,
        todo_pending=todo_pending,
        immediate_done=immediate_done,
        immediate_pending=immediate_pending,
        conditional_done=conditional_done,
        conditional_pending=conditional_pending,
    )
    update_roadmap(roadmap_path=roadmap_path, dashboard_md=dashboard_md)


if __name__ == "__main__":
    main()
