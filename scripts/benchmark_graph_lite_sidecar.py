from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services import graph_lite_service


def _read_fixtures(path: Path, bucket: str) -> list[dict[str, object]]:
    fixtures: list[dict[str, object]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"Fixture record must be an object at {path}:{line_number}")
        if str(payload.get("bucket", "")) != bucket:
            continue
        fixtures.append(payload)
    return fixtures


def build_markdown_report(payload: dict[str, object]) -> str:
    summary = payload.get("summary", {})
    lines = [
        "# Graph-Lite Relation Sidecar PoC Report (2026-04-28)",
        "",
        "## Scope",
        "- Local JSONL relation snapshot loader and in-memory relation search only.",
        "- No Neo4j, external DB, network call, paid API, or default `/query` route integration.",
        "- This measures graph-lite retrieval viability before answer-generation integration.",
        "",
        "## Summary",
        f"- fixture_bucket: `{payload.get('fixture_bucket', '-')}`",
        f"- snapshot_dir: `{payload.get('snapshot_dir', '-')}`",
        f"- questions: `{summary.get('questions', 0)}`",
        f"- hits: `{summary.get('hits', 0)}`",
        f"- fallbacks: `{summary.get('fallbacks', 0)}`",
        f"- avg_latency_ms: `{summary.get('avg_latency_ms', 0)}`",
        f"- avg_relation_count: `{summary.get('avg_relation_count', 0)}`",
        "",
        "## Results",
    ]

    results = payload.get("results", [])
    if isinstance(results, list):
        for item in results:
            if not isinstance(item, dict):
                continue
            lines.extend(
                [
                    f"### {item.get('id', '-')}",
                    f"- status: `{item.get('status', '-')}`",
                    f"- fallback_reason: `{item.get('fallback_reason') or '-'}`",
                    f"- query_entities: `{', '.join(item.get('query_entities', [])) or '-'}`",
                    f"- matched_entities: `{', '.join(item.get('matched_entities', [])) or '-'}`",
                    f"- relation_count: `{item.get('relation_count', 0)}`",
                    f"- latency_ms: `{item.get('latency_ms', 0)}`",
                ]
            )

    lines.extend(
        [
            "",
            "## Interpretation",
            "- A hit means graph-lite found relation evidence that can be appended to RAG context.",
            "- A fallback is expected for non relation-heavy questions or missing entity/relation coverage.",
            "- Answer quality still requires a separate `/query` quality comparison after graph context is wired in.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark local graph-lite relation sidecar retrieval.")
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        default=Path("docs/reports/graphrag_snapshot_2026-03-17"),
        help="Directory containing entities.jsonl, relations.jsonl, and optional ingest_stats.json.",
    )
    parser.add_argument("--fixtures", type=Path, default=Path("evals/answer_level_eval_fixtures.jsonl"))
    parser.add_argument("--bucket", default="graph-candidate")
    parser.add_argument("--max-hops", type=int, default=2)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("docs/reports/graph_lite_sidecar_poc_2026-04-28.json"),
    )
    parser.add_argument(
        "--output-report",
        type=Path,
        default=Path("docs/reports/GRAPH_LITE_SIDECAR_POC_2026-04-28.md"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    snapshot = graph_lite_service.load_relation_snapshot(args.snapshot_dir)
    fixtures = _read_fixtures(args.fixtures, args.bucket)
    results: list[dict[str, object]] = []
    latency_values: list[float] = []
    relation_counts: list[int] = []
    hit_count = 0

    for fixture in fixtures:
        result = graph_lite_service.query_relation_snapshot(
            snapshot,
            str(fixture.get("query", "")),
            collection_keys=[str(item) for item in fixture.get("collection_keys", []) if str(item).strip()],
            max_hops=args.max_hops,
            limit=args.limit,
        )
        relation_count = len(result.get("relations", [])) if isinstance(result.get("relations"), list) else 0
        if result.get("status") == "hit":
            hit_count += 1
        latency_values.append(float(result.get("latency_ms", 0)))
        relation_counts.append(relation_count)
        results.append(
            {
                "id": fixture.get("id"),
                "relation_shape": fixture.get("relation_shape"),
                "status": result.get("status"),
                "fallback_reason": result.get("fallback_reason"),
                "query_entities": result.get("query_entities", []),
                "matched_entities": result.get("matched_entities", []),
                "relation_count": relation_count,
                "latency_ms": result.get("latency_ms", 0),
            }
        )

    summary = {
        "questions": len(results),
        "hits": hit_count,
        "fallbacks": len(results) - hit_count,
        "avg_latency_ms": round(sum(latency_values) / len(latency_values), 3) if latency_values else 0.0,
        "avg_relation_count": round(sum(relation_counts) / len(relation_counts), 3) if relation_counts else 0.0,
        "max_hops": args.max_hops,
        "limit": args.limit,
    }
    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "contract_version": graph_lite_service.GRAPH_LITE_CONTRACT_VERSION,
        "snapshot_dir": str(args.snapshot_dir),
        "snapshot_stats": snapshot.stats,
        "fixture_bucket": args.bucket,
        "summary": summary,
        "results": results,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.write_text(build_markdown_report(payload), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
