from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts import session_closeout

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_build_report_blocks_when_harness_is_not_ready():
    def fake_run(command, cwd):
        return session_closeout.CommandResult(command=command, returncode=0, stdout="", stderr="")

    report = session_closeout.build_closeout_report(
        harness_report={
            "ready": False,
            "errors": ["active mismatch"],
            "warnings": [],
            "git": {"tracked_dirty_paths": []},
        },
        run_command=fake_run,
    )

    assert report["ready"] is False
    assert "roadmap_harness validate failed" in report["errors"]
    assert "active mismatch" in report["errors"]


def test_build_report_blocks_dirty_worktree_by_default():
    def fake_run(command, cwd):
        return session_closeout.CommandResult(command=command, returncode=0, stdout="", stderr="")

    report = session_closeout.build_closeout_report(
        harness_report={
            "ready": True,
            "errors": [],
            "warnings": [],
            "git": {"tracked_dirty_paths": ["TODO.md"]},
        },
        run_command=fake_run,
    )

    assert report["ready"] is False
    assert "worktree changes remain; commit or rerun with --allow-dirty for a WIP handoff" in report["errors"]


def test_build_report_allows_dirty_worktree_with_explicit_wip_flag():
    def fake_run(command, cwd):
        return session_closeout.CommandResult(command=command, returncode=0, stdout="", stderr="")

    report = session_closeout.build_closeout_report(
        harness_report={
            "ready": True,
            "errors": [],
            "warnings": [],
            "git": {"tracked_dirty_paths": ["TODO.md"]},
        },
        run_command=fake_run,
        allow_dirty=True,
    )

    assert report["ready"] is True
    assert "worktree changes allowed by --allow-dirty" in report["warnings"]


def test_build_report_blocks_when_diff_check_fails():
    def fake_run(command, cwd):
        if command == ["git", "diff", "--check"]:
            return session_closeout.CommandResult(
                command=command,
                returncode=1,
                stdout="TODO.md:10: trailing whitespace",
                stderr="",
            )
        return session_closeout.CommandResult(command=command, returncode=0, stdout="", stderr="")

    report = session_closeout.build_closeout_report(
        harness_report={
            "ready": True,
            "errors": [],
            "warnings": [],
            "git": {"tracked_dirty_paths": []},
        },
        run_command=fake_run,
    )

    assert report["ready"] is False
    assert "git diff --check failed" in report["errors"]


def test_script_can_run_directly_from_repo_root():
    result = subprocess.run(
        [sys.executable, "scripts/session_closeout.py", "--help"],
        cwd=ROOT_DIR,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Run the standard project session closeout checks" in result.stdout
