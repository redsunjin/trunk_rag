from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from core.settings import DEFAULT_COLLECTION_KEY
from services import graph_lite_service, graphrag_poc_service

DEFAULT_GRAPH_LITE_OUTPUT_DIR = Path("chroma_db/graph_lite_snapshot")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_graph_lite_snapshot(collection_key: str = DEFAULT_COLLECTION_KEY) -> dict[str, object]:
    snapshot = graphrag_poc_service.build_graph_snapshot(collection_key=collection_key)
    stats = dict(snapshot.get("stats", {}))
    stats.update(
        {
            "contract_version": graph_lite_service.GRAPH_LITE_CONTRACT_VERSION,
            "builder": "graph_lite_snapshot_builder.v1",
            "collection_key": collection_key,
            "generated_at": utc_now_iso(),
        }
    )
    return {
        "nodes": list(snapshot.get("nodes", [])) if isinstance(snapshot.get("nodes"), list) else [],
        "edges": list(snapshot.get("edges", [])) if isinstance(snapshot.get("edges"), list) else [],
        "stats": stats,
    }


def export_graph_lite_snapshot(snapshot: dict[str, object], output_dir: str | Path) -> dict[str, object]:
    output_path = Path(output_dir)
    paths = graphrag_poc_service.export_snapshot_jsonl(snapshot, output_path)
    loaded = graph_lite_service.load_relation_snapshot(output_path)
    return {
        "output_dir": str(output_path),
        "paths": paths,
        "stats": loaded.stats,
        "entity_count": len(loaded.entities),
        "relation_count": len(loaded.relations),
    }


def build_and_export_graph_lite_snapshot(
    *,
    collection_key: str = DEFAULT_COLLECTION_KEY,
    output_dir: str | Path = DEFAULT_GRAPH_LITE_OUTPUT_DIR,
) -> dict[str, object]:
    snapshot = build_graph_lite_snapshot(collection_key=collection_key)
    exported = export_graph_lite_snapshot(snapshot, output_dir)
    return {
        "contract_version": graph_lite_service.GRAPH_LITE_CONTRACT_VERSION,
        "collection_key": collection_key,
        "generated_at": snapshot["stats"].get("generated_at"),
        **exported,
    }


def build_markdown_report(payload: dict[str, object]) -> str:
    stats = payload.get("stats", {}) if isinstance(payload.get("stats"), dict) else {}
    paths = payload.get("paths", {}) if isinstance(payload.get("paths"), dict) else {}
    lines = [
        "# Graph-Lite Snapshot Build Report",
        "",
        "## Scope",
        "- Builds a local graph-lite JSONL snapshot from current seed and managed active markdown sources.",
        "- No Neo4j, external graph database, network call, paid API, or default Balanced route activation.",
        "- The generated directory can be used with `DOC_RAG_GRAPH_LITE_SNAPSHOT_DIR` for Quality opt-in queries.",
        "",
        "## Summary",
        f"- collection_key: `{payload.get('collection_key', '-')}`",
        f"- output_dir: `{payload.get('output_dir', '-')}`",
        f"- source_docs: `{stats.get('source_docs', 0)}`",
        f"- section_hits: `{stats.get('section_hits', 0)}`",
        f"- entities: `{payload.get('entity_count', 0)}`",
        f"- relations: `{payload.get('relation_count', 0)}`",
        f"- contract_version: `{payload.get('contract_version', '-')}`",
        "",
        "## Files",
        f"- entities: `{paths.get('entities', '-')}`",
        f"- relations: `{paths.get('relations', '-')}`",
        f"- stats: `{paths.get('stats', '-')}`",
        "",
        "## Next",
        f"- Set `DOC_RAG_GRAPH_LITE_SNAPSHOT_DIR={payload.get('output_dir', '-')}` to use this snapshot.",
        "- Keep graph-lite on the Quality opt-in path until real-user document quality is evaluated.",
    ]
    return "\n".join(lines) + "\n"


def write_build_summary(payload: dict[str, object], *, output_dir: str | Path) -> dict[str, str]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    summary_json_path = output_path / "build_summary.json"
    summary_report_path = output_path / "BUILD_REPORT.md"
    summary_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_report_path.write_text(build_markdown_report(payload), encoding="utf-8")
    return {
        "summary_json": str(summary_json_path),
        "summary_report": str(summary_report_path),
    }
