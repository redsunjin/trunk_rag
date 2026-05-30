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
SYNC_DOC_PATHS = {"TODO.md", "NEXT_SESSION_PLAN.md"}
VALID_STATUSES = {"active", "pending", "blocked", "done", "archived"}
VALID_VERSION_TRACKS = {"V1", "V1.5", "V2", "V3"}
VALID_HARNESS_MODES = {
    "v1_operating_loop",
    "v1_5_agent_ready_loop",
    "v2_single_agent_loop",
    "v3_agent_system_loop",
}
ISO_DATE_PATTERN = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")


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


def get_head_commit(root_dir: Path = ROOT_DIR) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root_dir,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    commit = result.stdout.strip()
    return commit or None


def get_tracked_dirty_paths(root_dir: Path = ROOT_DIR) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=root_dir,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


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


def find_stale_title_date_warning(text: str) -> str | None:
    title_date = None
    heading_dates: list[str] = []

    for line in text.splitlines():
        if not line.startswith("#"):
            continue
        match = ISO_DATE_PATTERN.search(line)
        if not match:
            continue
        date_value = match.group(1)
        heading_dates.append(date_value)
        if line.startswith("# ") and title_date is None:
            title_date = date_value

    if not title_date or not heading_dates:
        return None

    latest_heading_date = max(heading_dates)
    if title_date >= latest_heading_date:
        return None
    return (
        "NEXT_SESSION_PLAN title date is older than latest dated heading: "
        f"{title_date} < {latest_heading_date}"
    )


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
    head_commit: str | None = None,
    tracked_dirty_paths: list[str] | None = None,
) -> dict[str, object]:
    queue = parse_execution_queue(todo_text)
    session = parse_session_loop_harness(next_session_text)
    queue_validation = validate_queue(queue)
    active_item = queue_validation["active_item"]
    session_active_id = session.get("current_active_id", "")
    session_active_title = session.get("current_active_title", "")
    version_track = session.get("current_version_track", "")
    harness_mode = session.get("current_harness_mode", "")
    branch_execution_policy = session.get("branch_execution_policy", "")
    branch_plan_doc = session.get("branch_plan_doc", "")
    errors: list[str] = []
    warnings: list[str] = []
    required_session_keys = {
        "current_active_id",
        "current_active_title",
        "current_version_track",
        "current_harness_mode",
        "session_start_command",
        "default_regression_gate",
        "branch_execution_policy",
        "branch_plan_doc",
        "closeout_rule",
        "blocked_rule",
        "promotion_rule",
        "progress_sync_rule",
        "commit_sync_rule",
    }
    tracked_dirty_paths = tracked_dirty_paths or []
    dirty_sync_docs = sorted(path for path in tracked_dirty_paths if path in SYNC_DOC_PATHS)
    counts = {status: 0 for status in VALID_STATUSES}
    for row in queue:
        status = row["status"]
        if status in counts:
            counts[status] += 1

    if queue_validation["duplicate_ids"]:
        errors.append(f"Duplicate ids: {', '.join(queue_validation['duplicate_ids'])}")
    if queue_validation["invalid_statuses"]:
        errors.append(f"Invalid statuses: {', '.join(queue_validation['invalid_statuses'])}")
    missing_session_keys = sorted(required_session_keys - set(session.keys()))
    if missing_session_keys:
        errors.append(f"Session Loop Harness missing keys: {', '.join(missing_session_keys)}")
    if version_track and version_track not in VALID_VERSION_TRACKS:
        errors.append(f"Invalid current_version_track: {version_track}")
    if harness_mode and harness_mode not in VALID_HARNESS_MODES:
        errors.append(f"Invalid current_harness_mode: {harness_mode}")
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
    if branch_plan_doc and branch_plan_doc != "-":
        branch_plan_path = ROOT_DIR / branch_plan_doc
        if not branch_plan_path.exists():
            errors.append(f"branch_plan_doc does not exist: {branch_plan_doc}")
    if current_branch in {"main", "HEAD"} and branch_plan_doc and branch_plan_doc != "-":
        warnings.append(
            "branch_plan_doc is set while on main/HEAD; confirm whether this branch-scoped plan "
            "should remain active in NEXT_SESSION_PLAN."
        )
    if current_branch and current_branch not in {"main", "HEAD"} and not branch_execution_policy:
        errors.append("branch_execution_policy is required on non-main branches")
    if counts["pending"] == 0:
        warnings.append(
            "No pending item is queued after the active loop; automatic next-session promotion will stop "
            "when the current active item closes."
        )
    stale_title_date_warning = find_stale_title_date_warning(next_session_text)
    if stale_title_date_warning:
        warnings.append(stale_title_date_warning)
    if tracked_dirty_paths and not dirty_sync_docs:
        warnings.append(
            "Tracked worktree changes exist without TODO.md or NEXT_SESSION_PLAN.md updates; "
            "refresh the handoff docs before pausing or committing."
        )

    return {
        "ready": not errors,
        "errors": errors,
        "warnings": warnings,
        "active_item": active_item,
        "queue": queue,
        "counts": counts,
        "session": session,
        "branch": current_branch,
        "git": {
            "head_commit": head_commit,
            "tracked_dirty_paths": tracked_dirty_paths,
            "sync_docs_dirty": dirty_sync_docs,
        },
    }


def load_report(todo_path: Path = TODO_PATH, next_session_path: Path = NEXT_SESSION_PLAN_PATH) -> dict[str, object]:
    return build_report(
        todo_text=read_text(todo_path),
        next_session_text=read_text(next_session_path),
        current_branch=get_current_branch(),
        head_commit=get_head_commit(),
        tracked_dirty_paths=get_tracked_dirty_paths(),
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
    git_info = report.get("git", {})
    if git_info.get("head_commit"):
        print(f"  head={git_info['head_commit']}")
    tracked_dirty_paths = git_info.get("tracked_dirty_paths", [])
    print(f"  tracked_dirty={bool(tracked_dirty_paths)}")
    if git_info.get("sync_docs_dirty"):
        print(f"  sync_docs_dirty={','.join(git_info['sync_docs_dirty'])}")
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
    print(f"  version={session.get('current_version_track', '-')}")
    print(f"  harness_mode={session.get('current_harness_mode', '-')}")
    print(f"  start={session.get('session_start_command', '-')}")
    print(f"  gate={session.get('default_regression_gate', '-')}")
    print(f"  branch_policy={session.get('branch_execution_policy', '-')}")
    print(f"  branch_plan_doc={session.get('branch_plan_doc', '-')}")
    print(f"  progress_sync={session.get('progress_sync_rule', '-')}")
    print(f"  commit_sync={session.get('commit_sync_rule', '-')}")
    print(f"  closeout={session.get('closeout_rule', '-')}")
    if report["errors"]:
        print("  errors:")
        for error in report["errors"]:
            print(f"    - {error}")
    if report.get("warnings"):
        print("  warnings:")
        for warning in report["warnings"]:
            print(f"    - {warning}")


def _format_queue_item(item: dict[str, str]) -> str:
    return f"{item['id']} {item['title']}"


def _latest_done_items(queue: list[dict[str, str]], active_item: dict[str, str] | None, limit: int = 3) -> list[dict[str, str]]:
    if not queue:
        return []
    active_index = None
    if active_item:
        for index, item in enumerate(queue):
            if item["id"] == active_item["id"]:
                active_index = index
                break
    candidate_queue = queue[:active_index] if active_index is not None else queue
    done_items = [item for item in candidate_queue if item["status"] == "done"]
    if not done_items and active_index is not None:
        done_items = [item for item in queue if item["status"] == "done"]
    return list(reversed(done_items[-limit:]))


def build_progress_summary(report: dict[str, object]) -> dict[str, object]:
    queue = list(report.get("queue", []))
    active_item = report.get("active_item")
    pending_items = [item for item in queue if item["status"] == "pending"]
    blocked_items = [item for item in queue if item["status"] == "blocked"]
    remaining_items: list[dict[str, str]] = []
    if isinstance(active_item, dict):
        remaining_items.append(active_item)
    remaining_items.extend(pending_items)
    return {
        "active_item": active_item,
        "latest_done_items": _latest_done_items(queue, active_item if isinstance(active_item, dict) else None),
        "remaining_items": remaining_items,
        "blocked_items": blocked_items,
        "next_action": active_item,
    }


def format_progress_report(report: dict[str, object]) -> str:
    state = "ready" if report["ready"] else "blocked"
    summary = build_progress_summary(report)
    active_item = summary["active_item"]
    git_info = report.get("git", {})
    tracked_dirty_paths = git_info.get("tracked_dirty_paths", [])
    counts = report["counts"]
    lines = [f"[roadmap-harness-report] {state}"]

    lines.append("현재 위치:")
    if isinstance(active_item, dict):
        lines.append(f"- active: {_format_queue_item(active_item)}")
        lines.append(f"- 검증: {active_item['verify']}")
    else:
        lines.append("- active: 없음")

    lines.append("")
    lines.append("이번에 완료한 것:")
    latest_done_items = summary["latest_done_items"]
    if latest_done_items:
        for item in latest_done_items:
            lines.append(f"- {_format_queue_item(item)}")
    else:
        lines.append("- 없음")

    lines.append("")
    lines.append("남은 것:")
    remaining_items = summary["remaining_items"]
    if remaining_items:
        for item in remaining_items:
            lines.append(f"- {_format_queue_item(item)} ({item['status']})")
    else:
        lines.append("- 없음")

    lines.append("")
    lines.append("막힌 것:")
    blocked_items = summary["blocked_items"]
    if blocked_items:
        for item in blocked_items:
            lines.append(f"- {_format_queue_item(item)} ({item['status']})")
    else:
        lines.append("- 없음")

    lines.append("")
    lines.append("다음 실행:")
    next_action = summary["next_action"]
    if isinstance(next_action, dict):
        lines.append(f"- {next_action['id']}부터 진행")
    else:
        lines.append("- 새 active 항목 지정 필요")

    lines.append("")
    lines.append("상태:")
    if report.get("branch"):
        lines.append(f"- branch: {report['branch']}")
    if git_info.get("head_commit"):
        lines.append(f"- head: {git_info['head_commit']}")
    lines.append(f"- tracked_worktree: {'dirty' if tracked_dirty_paths else 'clean'}")
    lines.append(
        "- queue:"
        f" done={counts['done']}"
        f" active={counts['active']}"
        f" pending={counts['pending']}"
        f" blocked={counts['blocked']}"
        f" archived={counts['archived']}"
    )

    if report["errors"]:
        lines.append("")
        lines.append("오류:")
        for error in report["errors"]:
            lines.append(f"- {error}")
    if report.get("warnings"):
        lines.append("")
        lines.append("주의:")
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    return "\n".join(lines)


def print_progress_report(report: dict[str, object]) -> None:
    print(format_progress_report(report))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and display the roadmap loop harness state.")
    parser.add_argument("command", choices=["status", "validate", "report"])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--todo", type=Path, default=TODO_PATH)
    parser.add_argument("--next-session", type=Path, default=NEXT_SESSION_PLAN_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = load_report(todo_path=args.todo, next_session_path=args.next_session)

    if args.json:
        payload = dict(report)
        if args.command == "report":
            payload["progress_summary"] = build_progress_summary(report)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.command == "report":
        print_progress_report(report)
    else:
        print_status(report)

    if args.command == "validate":
        return 0 if report["ready"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
