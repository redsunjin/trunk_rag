from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app_api


DEFAULT_SCENARIOS: dict[str, list[str]] = {
    "single_all": ["all"],
    "single_fr": ["fr"],
    "dual_fr_ge": ["fr", "ge"],
}

DEFAULT_QUERIES = [
    "프랑스와 독일의 대표적인 과학자 업적을 비교해줘",
    "프랑스의 과학 혁신 사례를 요약해줘",
    "독일의 과학 발전 특징을 알려줘",
    "유럽 과학사에서 프랑스와 독일의 공통점을 정리해줘",
    "근대 과학 발전에 기여한 인물들을 정리해줘",
]


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * ratio
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    if low == high:
        return float(ordered[low])
    fraction = position - low
    return float(ordered[low] + (ordered[high] - ordered[low]) * fraction)


def parse_collection_keys(raw: str) -> list[str]:
    keys = [part.strip().lower() for part in raw.split(",") if part.strip()]
    deduped: list[str] = []
    seen: set[str] = set()
    for key in keys:
        if key in seen:
            continue
        seen.add(key)
        deduped.append(key)
    if not deduped:
        raise ValueError(f"Invalid collection spec: {raw}")
    if len(deduped) > app_api.MAX_QUERY_COLLECTIONS:
        raise ValueError(
            f"Up to {app_api.MAX_QUERY_COLLECTIONS} collections are supported: {raw}"
        )
    for key in deduped:
        app_api.get_collection_config(key)
    return deduped


def collect_docs_for_query(query: str, collection_keys: list[str]):
    docs = []
    fingerprints: set[str] = set()
    for key in collection_keys:
        db = app_api.get_db(key)
        retriever = db.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": app_api.SEARCH_K,
                "fetch_k": app_api.SEARCH_FETCH_K,
                "lambda_mult": app_api.SEARCH_LAMBDA,
            },
        )
        for item in retriever.invoke(query):
            source = str(item.metadata.get("source", ""))
            h2 = str(item.metadata.get("h2", ""))
            fingerprint = f"{source}|{h2}|{item.page_content}"
            if fingerprint in fingerprints:
                continue
            fingerprints.add(fingerprint)
            docs.append(item)

    max_docs = max(app_api.SEARCH_K * len(collection_keys), app_api.SEARCH_K)
    return docs[:max_docs]


def ensure_indexed(collection_keys: Iterable[str]) -> dict[str, dict[str, object]]:
    stats: dict[str, dict[str, object]] = {}
    for key in collection_keys:
        result = app_api.reindex(reset=True, collection_key=key)
        stats[key] = {
            "collection": result["collection"],
            "vectors": result["vectors"],
            "docs": result["docs"],
        }
    return stats


def benchmark_scenario(
    *,
    name: str,
    collection_keys: list[str],
    queries: list[str],
    rounds: int,
) -> dict[str, object]:
    latencies_ms: list[float] = []
    doc_counts: list[int] = []
    source_counts: list[int] = []

    for _ in range(rounds):
        for query in queries:
            started = time.perf_counter()
            docs = collect_docs_for_query(query=query, collection_keys=collection_keys)
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            latencies_ms.append(elapsed_ms)
            doc_counts.append(len(docs))
            source_counts.append(len({str(doc.metadata.get("source", "")) for doc in docs}))

    return {
        "name": name,
        "collection_keys": collection_keys,
        "collection_names": [app_api.get_collection_name(key) for key in collection_keys],
        "measurements": len(latencies_ms),
        "latency_avg_ms": round(mean(latencies_ms), 3) if latencies_ms else 0.0,
        "latency_p50_ms": round(percentile(latencies_ms, 0.5), 3),
        "latency_p95_ms": round(percentile(latencies_ms, 0.95), 3),
        "docs_avg": round(mean(doc_counts), 3) if doc_counts else 0.0,
        "source_count_avg": round(mean(source_counts), 3) if source_counts else 0.0,
    }


def build_scenarios(custom_specs: list[str] | None) -> dict[str, list[str]]:
    if not custom_specs:
        return DEFAULT_SCENARIOS
    scenarios: dict[str, list[str]] = {}
    for raw in custom_specs:
        keys = parse_collection_keys(raw)
        scenario_name = "custom_" + "_".join(keys)
        scenarios[scenario_name] = keys
    return scenarios


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark retrieval latency/coverage for single vs dual collections."
    )
    parser.add_argument(
        "--scenario",
        action="append",
        help="Collection keys joined by comma. Example: fr,ge (up to 2 keys).",
    )
    parser.add_argument(
        "--query",
        action="append",
        help="Custom benchmark query. Can be used multiple times.",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=5,
        help="How many rounds to execute for each query (default: 5).",
    )
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Reindex target collections before benchmark.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON output file path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.rounds < 1:
        raise ValueError("--rounds must be >= 1")

    scenarios = build_scenarios(args.scenario)
    queries = args.query if args.query else DEFAULT_QUERIES

    target_keys = sorted({key for keys in scenarios.values() for key in keys})
    index_stats: dict[str, dict[str, object]] = {}
    if args.reindex:
        index_stats = ensure_indexed(target_keys)

    results = []
    for name, keys in scenarios.items():
        results.append(
            benchmark_scenario(
                name=name,
                collection_keys=keys,
                queries=queries,
                rounds=args.rounds,
            )
        )

    payload = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "rounds": args.rounds,
        "queries": queries,
        "reindexed": args.reindex,
        "index_stats": index_stats,
        "results": results,
    }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
