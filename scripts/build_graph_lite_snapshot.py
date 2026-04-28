from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.settings import DEFAULT_COLLECTION_KEY
from services import graph_lite_snapshot_builder


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a local graph-lite JSONL relation snapshot from current markdown sources."
    )
    parser.add_argument("--collection-key", default=DEFAULT_COLLECTION_KEY)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=graph_lite_snapshot_builder.DEFAULT_GRAPH_LITE_OUTPUT_DIR,
        help="Directory to write entities.jsonl, relations.jsonl, ingest_stats.json, and build summary.",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Do not write build_summary.json and BUILD_REPORT.md.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = graph_lite_snapshot_builder.build_and_export_graph_lite_snapshot(
        collection_key=args.collection_key,
        output_dir=args.output_dir,
    )
    if not args.no_summary:
        payload["summary_paths"] = graph_lite_snapshot_builder.write_build_summary(
            payload,
            output_dir=args.output_dir,
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
