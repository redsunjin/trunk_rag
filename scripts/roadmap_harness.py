from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
TODO_PATH = ROOT_DIR / "TODO.md"
NEXT_SESSION_PLAN_PATH = ROOT_DIR / "NEXT_SESSION_PLAN.md"
VALID_STATUSES = {"active", "pending", "blocked", "done", "archived"}


def get_current_branch(root_dir: Path = ROOT_DIR) -> str | None:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=root_dir,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    branch = result.stdout.strip()
    return branch or None


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_section(text: str, heading: str) -> str:
    lines = text.splitlines()
    capture = False
    captured: list[str] = []
    target_level = None
    pattern = re.compile(r"^(#+)\s+(.*)$")

    for line in lines:
        match = pattern.match(line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            if title == heading:
                capture = True
                target_level = level
                continue
            if capture and target_level is not None and level <= target_level:
                break
        if capture:
            captured.append(line)
    if not captured:
        raise ValueError(f"Section not found: {heading}")
    return "\n".join(captured).strip()


def parse_markdown_table(section_text: str) -> list[dict[str, str]]:
    table_lines = [line.strip() for line in section_text.splitlines() if line.strip().startswith("|")]
    if len(table_lines) < 3:
        raise ValueError("Markdown table not found or incomplete.")

    headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != len(headers):
            raise ValueError(f"Malformed table row: {line}")
        rows.append(dict(zip(headers, cells)))
    return rows


def parse_execution_queue(text: str) -> list[dict[str, str]]:
    queue_section = extract_section(text, "Execution Queue")
    rows = parse_markdown_table(queue_section)
    required_headers = {"id", "status", "title", "verify"}
    missing_headers = required_headers - set(rows[0].keys()) if rows else required_headers
    if missing_headers:
        raise ValueError(f"Execution Queue missing headers: {sorted(missing_headers)}")
    return rows


def parse_key_value_bullets(section_text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    pattern = re.compile(r"^- ([a-z_]+): (.+)$")
    for raw_line in section_text.splitlines():
        line = raw_line.strip()
        match = pattern.match(line)
        if match:
            value = match.group(2).strip()
            if value.startswith("`") and value.endswith("`"):
                value = value[1:-1]
            result[match.group(1)] = value
    if not result:
        raise ValueError("No key/value bullets found.")
    return result


def parse_session_loop_harness(text: str) -> dict[str, str]:
    section = extract_section(text, "Session Loop Harness")
    return parse_key_value_bullets(section)


def validate_queue(rows: list[dict[str, str]]) -> dict[str, object]:
    ids = [row["id"] for row in rows]
    duplicate_ids = sorted({item_id for item_id in ids if ids.count(item_id) > 1})
    invalid_statuses = sorted(
        {
            row["status"]
            for row in rows
            if row["status"] not in VALID_STATUSES
        }
    )
    active_rows = [row for row in rows if row["status"] == "active"]
    return {
        "duplicate_ids": duplicate_ids,
        "invalid_statuses": invalid_statuses,
        "active_count": len(active_rows),
        "active_item": active_rows[0] if len(active_rows) == 1 else None,
    }


def build_report(
    *,
    todo_text: str,
    next_session_text: str,
    current_branch: str | None = None,
) -> dict[str, object]:
    queue = parse_execution_queue(todo_text)
    session = parse_session_loop_harness(next_session_text)
    queue_validation = validate_queue(queue)
    active_item = queue_validation["active_item"]
    session_active_id = session.get("current_active_id", "")
    session_active_title = session.get("current_active_title", "")
    errors: list[str] = []
    warnings: list[str] = []
    required_session_keys = {
        "current_active_id",
        "current_active_title",
        "session_start_command",
        "default_regression_gate",
        "closeout_rule",
        "blocked_rule",
        "promotion_rule",
    }

    if queue_validation["duplicate_ids"]:
        errors.append(f"Duplicate ids: {', '.join(queue_validation['duplicate_ids'])}")
    if queue_validation["invalid_statuses"]:
        errors.append(f"Invalid statuses: {', '.join(queue_validation['invalid_statuses'])}")
    missing_session_keys = sorted(required_session_keys - set(session.keys()))
    if missing_session_keys:
        errors.append(f"Session Loop Harness missing keys: {', '.join(missing_session_keys)}")
    if queue_validation["active_count"] != 1:
        errors.append(f"Expected exactly one active item, found {queue_validation['active_count']}")
    if active_item and session_active_id != active_item["id"]:
        errors.append(
            "NEXT_SESSION_PLAN current_active_id does not match TODO active item: "
            f"{session_active_id} != {active_item['id']}"
        )
    if active_item and session_active_title != active_item["title"]:
        errors.append(
            "NEXT_SESSION_PLAN current_active_title does not match TODO active title: "
            f"{session_active_title} != {active_item['title']}"
        )
    if current_branch and current_branch not in {"main", "HEAD"}:
        warnings.append(
            "Non-main branch detected; TODO/NEXT_SESSION active loop remains authoritative "
            "unless the user explicitly redirects or the queue is promoted."
        )

    counts = {status: 0 for status in VALID_STATUSES}
    for row in queue:
        status = row["status"]
        if status in counts:
            counts[status] += 1

    return {
        "ready": not errors,
        "errors": errors,
        "warnings": warnings,
        "active_item": active_item,
        "queue": queue,
        "counts": counts,
        "session": session,
        "branch": current_branch,
    }


def load_report(todo_path: Path = TODO_PATH, next_session_path: Path = NEXT_SESSION_PLAN_PATH) -> dict[str, object]:
    return build_report(
        todo_text=read_text(todo_path),
        next_session_text=read_text(next_session_path),
        current_branch=get_current_branch(),
    )


def print_status(report: dict[str, object]) -> None:
    state = "ready" if report["ready"] else "blocked"
    print(f"[roadmap-harness] {state}")
    active_item = report.get("active_item")
    if active_item:
        print(f"  active_id={active_item['id']}")
        print(f"  active_title={active_item['title']}")
        print(f"  verify={active_item['verify']}")
    branch = report.get("branch")
    if branch:
        print(f"  branch={branch}")
    counts = report["counts"]
    print(
        "  queue:"
        f" active={counts['active']}"
        f" pending={counts['pending']}"
        f" blocked={counts['blocked']}"
        f" done={counts['done']}"
        f" archived={counts['archived']}"
    )
    session = report["session"]
    print(f"  start={session.get('session_start_command', '-')}")
    print(f"  gate={session.get('default_regression_gate', '-')}")
    print(f"  closeout={session.get('closeout_rule', '-')}")
    if report["errors"]:
        print("  errors:")
        for error in report["errors"]:
            print(f"    - {error}")
    if report.get("warnings"):
        print("  warnings:")
        for warning in report["warnings"]:
            print(f"    - {warning}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and display the roadmap loop harness state.")
    parser.add_argument("command", choices=["status", "validate"])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--todo", type=Path, default=TODO_PATH)
    parser.add_argument("--next-session", type=Path, default=NEXT_SESSION_PLAN_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = load_report(todo_path=args.todo, next_session_path=args.next_session)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_status(report)

    if args.command == "validate":
        return 0 if report["ready"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
