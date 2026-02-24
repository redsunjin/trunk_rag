from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

from langchain_core.documents import Document

from common import COUNTRY_BY_STEM

HEADER_RE = re.compile(r"^(#{2,4})\s+(.+?)\s*$")
REQUIRED_METADATA_FIELDS = ("source", "country", "doc_type")
SECTION_MIN_BODY_LEN = 20
DOC_MIN_LEN = 200


def _compact_len(text: str) -> int:
    return len("".join(text.split()))


def _validate_metadata(source: str, metadata: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    for key in REQUIRED_METADATA_FIELDS:
        value = str(metadata.get(key, "")).strip()
        if not value:
            reasons.append(f"{source}: missing metadata `{key}`")
    return reasons


def validate_markdown_text(
    source: str,
    text: str,
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    metadata = metadata or {}
    reasons = _validate_metadata(source, metadata)
    warnings: list[str] = []

    normalized = text.strip()
    if _compact_len(normalized) < DOC_MIN_LEN:
        warnings.append(f"{source}: document length is under recommended {DOC_MIN_LEN} chars")

    lines = text.splitlines()
    header_positions: list[tuple[int, int, str]] = []
    seen_h2: str | None = None
    seen_h3: str | None = None
    seen_headers: set[tuple[int, str | None, str | None, str]] = set()

    for idx, raw_line in enumerate(lines):
        line = raw_line.strip()
        match = HEADER_RE.match(line)
        if not match:
            continue

        level = len(match.group(1))
        title = match.group(2).strip()
        title_key = title.lower()
        if len(title) < 2:
            warnings.append(f"{source}: short header title '{title}'")

        if level == 2:
            parent_h2 = None
            parent_h3 = None
            seen_h2 = title
            seen_h3 = None
        elif level == 3:
            if seen_h2 is None:
                warnings.append(f"{source}: '### {title}' appears before any '##' section")
            parent_h2 = seen_h2
            parent_h3 = None
            seen_h3 = title
        else:
            if seen_h3 is None:
                warnings.append(f"{source}: '#### {title}' appears before any '###' section")
            parent_h2 = seen_h2
            parent_h3 = seen_h3

        dedupe_key = (level, parent_h2, parent_h3, title_key)
        if dedupe_key in seen_headers:
            warnings.append(f"{source}: duplicated header '{title}' at level h{level}")
        seen_headers.add(dedupe_key)
        header_positions.append((idx, level, title))

    if not header_positions:
        warnings.append(f"{source}: no allowed headers(##/###/####) found")
    elif header_positions[0][1] != 2:
        warnings.append(f"{source}: first section should start with '##'")

    for index, (line_idx, _level, title) in enumerate(header_positions):
        next_line_idx = len(lines) if index + 1 >= len(header_positions) else header_positions[index + 1][0]
        body = "\n".join(lines[line_idx + 1 : next_line_idx]).strip()
        if _compact_len(body) < SECTION_MIN_BODY_LEN:
            warnings.append(
                f"{source}: section '{title}' body is under recommended {SECTION_MIN_BODY_LEN} chars"
            )

    return {
        "source": source,
        "usable": len(reasons) == 0,
        "reasons": reasons,
        "warnings": warnings,
    }


def validate_loaded_documents(docs: Iterable[Document]) -> list[dict[str, object]]:
    reports: list[dict[str, object]] = []
    for doc in docs:
        source = str(doc.metadata.get("source", "unknown"))
        reports.append(validate_markdown_text(source=source, text=doc.page_content, metadata=doc.metadata))
    return reports


def _validate_files(target: Path) -> list[dict[str, object]]:
    files: list[Path]
    if target.is_dir():
        files = sorted(target.glob("*.md"))
    else:
        files = [target]

    reports = []
    for path in files:
        stem = path.stem
        reports.append(
            validate_markdown_text(
                source=path.name,
                text=path.read_text(encoding="utf-8"),
                metadata={
                    "source": path.name,
                    "country": COUNTRY_BY_STEM.get(stem, "unknown"),
                    "doc_type": "summary" if stem == "eu_summry" else "country",
                },
            )
        )
    return reports


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate markdown docs for doc_rag ingest.")
    parser.add_argument("target", type=Path, nargs="?", default=Path("data"))
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    reports = _validate_files(args.target)
    summary = {
        "total_docs": len(reports),
        "usable_docs": sum(1 for report in reports if report["usable"]),
        "rejected_docs": sum(1 for report in reports if not report["usable"]),
        "warning_docs": sum(1 for report in reports if report["warnings"]),
        "reports": reports,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    print(
        f"total={summary['total_docs']} usable={summary['usable_docs']} "
        f"rejected={summary['rejected_docs']} warning_docs={summary['warning_docs']}"
    )
    for report in reports:
        status = "OK" if report["usable"] else "FAIL"
        warning_count = len(report["warnings"])
        print(f"- {report['source']}: {status} warnings={warning_count}")
        for reason in report["reasons"]:
            print(f"  reason: {reason}")


if __name__ == "__main__":
    main()
