from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts import roadmap_harness


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    def as_dict(self) -> dict[str, object]:
        return {
            "command": self.command,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


RunCommand = Callable[[list[str], Path], CommandResult]


def run_subprocess(command: list[str], cwd: Path) -> CommandResult:
    result = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    return CommandResult(
        command=command,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def _has_status_changes(status_output: str) -> bool:
    return any(line and not line.startswith("## ") for line in status_output.splitlines())


def build_closeout_report(
    *,
    harness_report: dict[str, object] | None = None,
    run_command: RunCommand = run_subprocess,
    root_dir: Path = ROOT_DIR,
    allow_dirty: bool = False,
) -> dict[str, object]:
    harness_report = harness_report or roadmap_harness.load_report()
    errors: list[str] = []
    warnings = list(harness_report.get("warnings", []))
    checks: dict[str, object] = {
        "roadmap_harness": {
            "ready": harness_report.get("ready", False),
            "active_item": harness_report.get("active_item"),
            "errors": harness_report.get("errors", []),
            "warnings": harness_report.get("warnings", []),
        }
    }

    if not harness_report.get("ready", False):
        errors.append("roadmap_harness validate failed")
        errors.extend(str(error) for error in harness_report.get("errors", []))

    diff_check = run_command(["git", "diff", "--check"], root_dir)
    git_status = run_command(["git", "status", "--short", "--branch"], root_dir)
    checks["git_diff_check"] = diff_check.as_dict()
    checks["git_status"] = git_status.as_dict()

    if diff_check.returncode != 0:
        errors.append("git diff --check failed")
    if git_status.returncode != 0:
        errors.append("git status --short --branch failed")

    git_info = harness_report.get("git", {})
    tracked_dirty_paths = []
    if isinstance(git_info, dict):
        tracked_dirty_paths = list(git_info.get("tracked_dirty_paths", []))
    has_dirty_status = _has_status_changes(git_status.stdout)
    if tracked_dirty_paths or has_dirty_status:
        if allow_dirty:
            warnings.append("worktree changes allowed by --allow-dirty")
        else:
            errors.append("worktree changes remain; commit or rerun with --allow-dirty for a WIP handoff")

    return {
        "ready": not errors,
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
    }


def print_closeout_report(report: dict[str, object]) -> None:
    state = "ready" if report["ready"] else "blocked"
    print(f"[session-closeout] {state}")

    checks = report.get("checks", {})
    harness_check = checks.get("roadmap_harness", {}) if isinstance(checks, dict) else {}
    active_item = harness_check.get("active_item") if isinstance(harness_check, dict) else None
    if isinstance(active_item, dict):
        print(f"  active_id={active_item.get('id', '-')}")
        print(f"  active_title={active_item.get('title', '-')}")

    if report.get("errors"):
        print("  errors:")
        for error in report["errors"]:
            print(f"    - {error}")
    if report.get("warnings"):
        print("  warnings:")
        for warning in report["warnings"]:
            print(f"    - {warning}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the standard project session closeout checks.")
    parser.add_argument("--allow-dirty", action="store_true", help="Allow WIP handoff with remaining worktree changes.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable closeout report.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_closeout_report(allow_dirty=args.allow_dirty)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_closeout_report(report)
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
