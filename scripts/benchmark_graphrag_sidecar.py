from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services import graphrag_poc_service


def build_markdown_report(payload: dict[str, object]) -> str:
    summary = payload.get("benchmark", {}).get("summary", {})
    lines = [
        "# GraphRAG Actual PoC Report (2026-03-17)",
        "",
        "## 범위",
        "- managed active docs를 포함한 현재 markdown 집합에서 graph snapshot을 생성한다.",
        "- graph-candidate 질문 6개를 대상으로 관계 확장 검색 latency와 expected entity coverage를 측정한다.",
        "- 이번 측정은 answer generation이 아니라 sidecar retrieval viability 확인 1차다.",
        "",
        "## Ingest Stats",
        f"- collection: `{payload.get('snapshot', {}).get('stats', {}).get('collection_key', 'all')}`",
        f"- source_docs: `{payload.get('snapshot', {}).get('stats', {}).get('source_docs', 0)}`",
        f"- section_hits: `{payload.get('snapshot', {}).get('stats', {}).get('section_hits', 0)}`",
        f"- nodes: `{payload.get('snapshot', {}).get('stats', {}).get('nodes', 0)}`",
        f"- edges: `{payload.get('snapshot', {}).get('stats', {}).get('edges', 0)}`",
        "",
        "## Benchmark Summary",
        f"- questions: `{summary.get('questions', 0)}`",
        f"- avg_latency_ms: `{summary.get('avg_latency_ms', 0)}`",
        f"- avg_expected_entity_hit_ratio: `{summary.get('avg_expected_entity_hit_ratio', 0)}`",
        f"- max_hops: `{summary.get('max_hops', 0)}`",
        "",
        "## Question Results",
    ]

    results = payload.get("benchmark", {}).get("results", [])
    if isinstance(results, list):
        for item in results:
            if not isinstance(item, dict):
                continue
            lines.extend(
                [
                    f"### {item.get('id', '-')}",
                    f"- latency_ms: `{item.get('latency_ms', 0)}`",
                    f"- expected_entity_hit_ratio: `{item.get('expected_entity_hit_ratio', 0)}`",
                    f"- query_entities: `{', '.join(item.get('query_entities', [])) or '-'}`",
                    f"- matched_entities: `{', '.join(item.get('matched_entities', [])) or '-'}`",
                    f"- sample_relations:",
                ]
            )
            relations = item.get("relations", [])
            if isinstance(relations, list) and relations:
                for relation in relations[:3]:
                    lines.append(f"  - {relation}")
            else:
                lines.append("  - none")

    lines.extend(
        [
            "",
            "## 해석",
            "- 이 결과는 graph snapshot 기반 관계 확장 검색이 현재 문서 집합에서 실제로 작동하는지 보는 1차 실측이다.",
            "- `expected_entity_hit_ratio`는 answer 정확도가 아니라 관계 후보 recall 성격의 지표다.",
            "- 현재 2-hop 확장은 일부 질문에서 그래프 전체로 넓게 퍼지므로 precision 측정은 아직 부족하다.",
            "- answer quality의 최종 개선 여부는 아직 확인되지 않았고, 다음 단계에서 vector baseline과 answer-level 비교가 추가로 필요하다.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and benchmark the GraphRAG sidecar PoC snapshot.")
    parser.add_argument("--collection", default="all")
    parser.add_argument("--max-hops", type=int, default=2)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("docs/reports/graphrag_actual_poc_2026-03-17.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/reports/graphrag_snapshot_2026-03-17"),
    )
    parser.add_argument(
        "--output-report",
        type=Path,
        default=Path("docs/reports/GRAPH_RAG_ACTUAL_POC_REPORT_2026-03-17.md"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    snapshot = graphrag_poc_service.build_graph_snapshot(collection_key=args.collection)
    export_paths = graphrag_poc_service.export_snapshot_jsonl(snapshot, args.output_dir)
    benchmark = graphrag_poc_service.benchmark_graph_candidates(snapshot, max_hops=args.max_hops)

    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "snapshot": {
            "stats": snapshot.get("stats", {}),
            "export_paths": export_paths,
        },
        "benchmark": benchmark,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.write_text(build_markdown_report(payload), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
