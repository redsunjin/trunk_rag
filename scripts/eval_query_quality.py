from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.settings import COLLECTION_CONFIGS, DEFAULT_COLLECTION_KEY, MAX_QUERY_COLLECTIONS
from services import graphrag_poc_service

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_SECONDS = 45
DEFAULT_EVAL_FILE = Path("evals/answer_level_eval_fixtures.jsonl")
DEFAULT_OUTPUT_JSON = Path("docs/reports/query_answer_eval_latest.json")
DEFAULT_OUTPUT_REPORT = Path("docs/reports/QUERY_ANSWER_EVAL_LATEST.md")
DEFAULT_BACKEND = "vector_query"
GRAPH_SNAPSHOT_MAX_COLLECTIONS = 3
REQUIRED_HEALTH_KEYS = {
    "status",
    "collection_key",
    "collection",
    "persist_dir",
    "vectors",
    "chunking_mode",
    "embedding_model",
    "default_llm_provider",
    "default_llm_model",
}
COLLECTION_NAME_TO_KEY = {
    str(config["name"]).strip().lower(): key for key, config in COLLECTION_CONFIGS.items()
}
COLLECTION_KEY_TO_NAME = {key: str(config["name"]).strip() for key, config in COLLECTION_CONFIGS.items()}


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


def normalize_text(value: object) -> str:
    return str(value or "").strip().lower()


def validate_health_payload(payload: dict[str, object]) -> None:
    missing = sorted(REQUIRED_HEALTH_KEYS - payload.keys())
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(
            "Unexpected /health payload. "
            f"Missing fields: {missing_text}. "
            "다른 프로젝트가 같은 포트를 사용 중인지 확인하세요."
        )
    if payload.get("status") != "ok":
        raise ValueError(f"Unexpected /health status: {payload.get('status')}")


def health_check(base_url: str, timeout_seconds: int) -> dict[str, object]:
    request = urllib.request.Request(f"{base_url}/health", method="GET")
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        payload = response.read()
    body = json.loads(payload.decode("utf-8"))
    validate_health_payload(body)
    return body


def collections_check(base_url: str, timeout_seconds: int) -> dict[str, object]:
    request = urllib.request.Request(f"{base_url}/collections", method="GET")
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        payload = response.read()
    body = json.loads(payload.decode("utf-8"))
    if not isinstance(body, dict) or not isinstance(body.get("collections"), list):
        raise ValueError("Unexpected /collections payload. 다른 프로젝트가 같은 포트를 사용 중인지 확인하세요.")
    return body


def load_eval_fixtures(
    path: Path,
    *,
    buckets: set[str] | None = None,
    case_ids: set[str] | None = None,
    max_cases: int | None = None,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"invalid fixture object at line {line_no}")
            record["_line_no"] = line_no
            bucket = str(record.get("bucket", "")).strip()
            case_id = str(record.get("id", "")).strip()
            if buckets and bucket not in buckets:
                continue
            if case_ids and case_id not in case_ids:
                continue
            records.append(record)
            if max_cases and len(records) >= max_cases:
                break
    if not records:
        raise ValueError(f"no eval fixtures selected from {path}")
    return records


def prepare_query_request(case: dict[str, object]) -> tuple[dict[str, object], list[str], str]:
    return prepare_query_request_for_backend(case, max_collection_keys=MAX_QUERY_COLLECTIONS)


def prepare_query_request_for_backend(
    case: dict[str, object],
    *,
    max_collection_keys: int,
) -> tuple[dict[str, object], list[str], str]:
    payload = {"query": case["query"]}
    collection_keys = [str(item).strip() for item in case.get("collection_keys", []) if str(item).strip()]
    if len(collection_keys) == 1:
        payload["collection"] = collection_keys[0]
        return payload, collection_keys, "explicit_single"
    if 1 < len(collection_keys) <= max_collection_keys:
        payload["collection"] = collection_keys[0]
        payload["collections"] = collection_keys
        return payload, collection_keys, "explicit_multi"
    payload["collection"] = DEFAULT_COLLECTION_KEY
    return payload, [DEFAULT_COLLECTION_KEY], "fallback_all_for_eval"


def build_query_payload(
    case: dict[str, object],
    *,
    llm_provider: str,
    llm_model: str | None,
    llm_base_url: str | None,
    llm_api_key: str | None,
) -> tuple[dict[str, object], list[str], str]:
    payload, expected_route_keys, request_mode = prepare_query_request(case)
    payload["llm_provider"] = llm_provider
    payload["llm_model"] = llm_model
    payload["llm_base_url"] = llm_base_url
    payload["llm_api_key"] = llm_api_key
    return payload, expected_route_keys, request_mode


def validate_fixture_collections_available(
    fixtures: list[dict[str, object]],
    collections_payload: dict[str, object],
) -> None:
    vector_counts = {
        str(item.get("key", "")).strip(): int(item.get("vectors", 0) or 0)
        for item in collections_payload.get("collections", [])
        if isinstance(item, dict)
    }
    missing_cases: list[str] = []
    for case in fixtures:
        payload, expected_route_keys, request_mode = prepare_query_request(case)
        if request_mode == "fallback_all_for_eval":
            continue
        if all(vector_counts.get(key, 0) > 0 for key in expected_route_keys):
            continue
        missing = [key for key in expected_route_keys if vector_counts.get(key, 0) <= 0]
        missing_cases.append(f"{case.get('id')}: {','.join(missing)}")

    if missing_cases:
        raise ValueError(
            "Selected eval fixtures require empty collections. "
            f"먼저 /reindex 또는 대상 컬렉션 준비가 필요합니다: {'; '.join(missing_cases)}"
        )


def call_query(
    *,
    base_url: str,
    timeout_seconds: int,
    request_id: str,
    payload: dict[str, object],
) -> tuple[int, dict[str, object], float, dict[str, str]]:
    endpoint = f"{base_url}/query"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Request-ID": request_id,
        },
    )
    started_at = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw_body = response.read()
            status = response.status
            headers = dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        raw_body = exc.read()
        status = exc.code
        headers = dict(exc.headers.items())
    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 3)
    try:
        response_body = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        response_body = {"detail": raw_body.decode("utf-8", errors="replace")}
    if not isinstance(response_body, dict):
        response_body = {"detail": response_body}
    return status, response_body, elapsed_ms, headers


def build_graph_snapshot_health(snapshot: dict[str, object], *, collection_key: str, max_hops: int) -> dict[str, object]:
    stats = dict(snapshot.get("stats", {}))
    return {
        "status": "ok",
        "collection_key": collection_key,
        "collection": f"graph_snapshot:{collection_key}",
        "persist_dir": "-",
        "vectors": stats.get("edges", 0),
        "chunking_mode": "graph_snapshot",
        "embedding_model": "graph_snapshot",
        "default_llm_provider": "graph_snapshot",
        "default_llm_model": "-",
        "graph_nodes": stats.get("nodes", 0),
        "graph_edges": stats.get("edges", 0),
        "graph_source_docs": stats.get("source_docs", 0),
        "graph_section_hits": stats.get("section_hits", 0),
        "graph_max_hops": max_hops,
    }


def call_graph_snapshot(
    *,
    snapshot: dict[str, object],
    question: str,
    route_keys: list[str],
    max_hops: int,
) -> tuple[int, dict[str, object], float, dict[str, str]]:
    result = graphrag_poc_service.answer_graph_snapshot(snapshot, question, max_hops=max_hops)
    collection_names = [COLLECTION_KEY_TO_NAME[key] for key in route_keys if key in COLLECTION_KEY_TO_NAME]
    headers: dict[str, str] = {}
    if collection_names:
        headers["X-RAG-Collections"] = ",".join(collection_names)
        headers["X-RAG-Collection"] = collection_names[0]
    body = {
        "answer": result["answer"],
        "mode": "graph_snapshot",
        "entities": result["matched_entities"],
        "relations": result["relations"],
    }
    return 200, body, float(result["latency_ms"]), headers


def extract_route_keys(headers: dict[str, str]) -> list[str]:
    raw_header = headers.get("X-RAG-Collections") or headers.get("x-rag-collections") or ""
    items = [item.strip() for item in raw_header.split(",") if item.strip()]
    if not items:
        single = headers.get("X-RAG-Collection") or headers.get("x-rag-collection") or ""
        if single.strip():
            items = [single.strip()]
    route_keys: list[str] = []
    for name in items:
        key = COLLECTION_NAME_TO_KEY.get(name.lower())
        if key:
            route_keys.append(key)
    return route_keys


def evaluate_case_result(
    case: dict[str, object],
    *,
    status: int,
    body: dict[str, object],
    headers: dict[str, str],
    latency_ms: float,
    expected_route_keys: list[str],
    request_mode: str,
) -> dict[str, object]:
    evaluation = dict(case.get("evaluation", {}))
    answer = str(body.get("answer", "") or "")
    normalized_answer = normalize_text(answer)
    must_include = [str(item) for item in evaluation.get("must_include", [])]
    must_not_include = [str(item) for item in evaluation.get("must_not_include", [])]
    must_include_any = [str(item) for item in evaluation.get("must_include_any", [])]
    min_answer_chars = int(evaluation.get("min_answer_chars", 0))

    required_hits = [term for term in must_include if normalize_text(term) in normalized_answer]
    forbidden_hits = [term for term in must_not_include if normalize_text(term) in normalized_answer]
    any_hits = [term for term in must_include_any if normalize_text(term) in normalized_answer]

    required_ratio = round(len(required_hits) / len(must_include), 4) if must_include else 1.0
    any_ratio = round(len(any_hits) / len(must_include_any), 4) if must_include_any else 1.0
    min_chars_ratio = round(min(len(answer.strip()) / min_answer_chars, 1.0), 4) if min_answer_chars else 1.0
    hallucination_score = round(
        1.0 - min(len(forbidden_hits) / max(len(must_not_include), 1), 1.0),
        4,
    )

    weights = dict(evaluation.get("score_weights", {}))
    precision_weight = float(weights.get("precision", 0.5))
    completeness_weight = float(weights.get("completeness", 0.4))
    hallucination_weight = float(weights.get("hallucination", 0.1))
    weight_total = precision_weight + completeness_weight + hallucination_weight
    if weight_total <= 0:
        raise ValueError(f"invalid score weights for case {case.get('id')}")

    precision_score = required_ratio
    completeness_score = round((any_ratio + min_chars_ratio) / 2, 4)
    weighted_score = (
        (precision_score * precision_weight)
        + (completeness_score * completeness_weight)
        + (hallucination_score * hallucination_weight)
    ) / weight_total

    actual_route_keys = extract_route_keys(headers)
    route_pass = actual_route_keys == expected_route_keys if actual_route_keys else False
    if not expected_route_keys:
        route_pass = True

    passed = (
        status == 200
        and required_ratio == 1.0
        and any_ratio > 0.0
        and min_chars_ratio == 1.0
        and not forbidden_hits
        and route_pass
    )
    result = {
        "id": case["id"],
        "bucket": case["bucket"],
        "query": case["query"],
        "request_mode": request_mode,
        "collection_keys": case.get("collection_keys", []),
        "expected_route_keys": expected_route_keys,
        "actual_route_keys": actual_route_keys,
        "route_pass": route_pass,
        "status": status,
        "latency_ms": latency_ms,
        "answer_length": len(answer.strip()),
        "answer_preview": answer[:240],
        "answer": answer,
        "required_hits": required_hits,
        "required_total": len(must_include),
        "required_ratio": required_ratio,
        "must_include_any_hits": any_hits,
        "must_include_any_total": len(must_include_any),
        "must_include_any_ratio": any_ratio,
        "forbidden_hits": forbidden_hits,
        "min_answer_chars": min_answer_chars,
        "min_chars_ratio": min_chars_ratio,
        "precision_score": precision_score,
        "completeness_score": completeness_score,
        "hallucination_score": hallucination_score,
        "weighted_score": round(weighted_score, 4),
        "pass": passed,
        "error_code": body.get("code"),
        "error_message": body.get("message"),
    }
    return result


def summarize_results(results: list[dict[str, object]]) -> dict[str, object]:
    latencies = [float(item["latency_ms"]) for item in results]
    scores = [float(item["weighted_score"]) for item in results]
    passed = sum(1 for item in results if item["pass"])
    buckets: dict[str, list[dict[str, object]]] = {}
    for item in results:
        buckets.setdefault(str(item["bucket"]), []).append(item)

    bucket_summaries: dict[str, dict[str, object]] = {}
    for bucket, bucket_items in buckets.items():
        bucket_latencies = [float(item["latency_ms"]) for item in bucket_items]
        bucket_scores = [float(item["weighted_score"]) for item in bucket_items]
        bucket_passed = sum(1 for item in bucket_items if item["pass"])
        bucket_summaries[bucket] = {
            "cases": len(bucket_items),
            "passed": bucket_passed,
            "pass_rate": round(bucket_passed / len(bucket_items), 4),
            "avg_latency_ms": round(mean(bucket_latencies), 3) if bucket_latencies else 0.0,
            "p95_latency_ms": round(percentile(bucket_latencies, 0.95), 3) if bucket_latencies else 0.0,
            "avg_weighted_score": round(mean(bucket_scores), 4) if bucket_scores else 0.0,
        }

    return {
        "cases": len(results),
        "passed": passed,
        "pass_rate": round(passed / len(results), 4) if results else 0.0,
        "avg_latency_ms": round(mean(latencies), 3) if latencies else 0.0,
        "p95_latency_ms": round(percentile(latencies, 0.95), 3) if latencies else 0.0,
        "avg_weighted_score": round(mean(scores), 4) if scores else 0.0,
        "bucket_summaries": bucket_summaries,
    }


def build_markdown_report(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    health = payload["health"]
    lines = [
        "# Query Answer Eval Report",
        "",
        "## Scope",
        f"- generated_at: `{payload['generated_at']}`",
        f"- backend: `{payload.get('backend', DEFAULT_BACKEND)}`",
        f"- eval_file: `{payload['eval_file']}`",
        f"- base_url: `{payload['base_url']}`",
        f"- llm_provider: `{payload['llm_provider']}`",
        f"- llm_model: `{payload['llm_model'] or health.get('default_llm_model', '-')}`",
        "",
        "## Health Snapshot",
        f"- vectors: `{health.get('vectors', 0)}`",
        f"- chunking_mode: `{health.get('chunking_mode', '-')}`",
        f"- embedding_model: `{health.get('embedding_model', '-')}`",
        f"- default_llm_provider: `{health.get('default_llm_provider', '-')}`",
        f"- default_llm_model: `{health.get('default_llm_model', '-')}`",
        "",
    ]

    if payload.get("backend") == "graph_snapshot":
        lines.extend(
            [
                "## Graph Snapshot",
                f"- graph_nodes: `{health.get('graph_nodes', 0)}`",
                f"- graph_edges: `{health.get('graph_edges', 0)}`",
                f"- graph_source_docs: `{health.get('graph_source_docs', 0)}`",
                f"- graph_section_hits: `{health.get('graph_section_hits', 0)}`",
                f"- graph_max_hops: `{health.get('graph_max_hops', 0)}`",
                "",
            ]
        )

    lines.extend(
        [
        "## Summary",
        f"- cases: `{summary['cases']}`",
        f"- passed: `{summary['passed']}`",
        f"- pass_rate: `{summary['pass_rate']}`",
        f"- avg_weighted_score: `{summary['avg_weighted_score']}`",
        f"- avg_latency_ms: `{summary['avg_latency_ms']}`",
        f"- p95_latency_ms: `{summary['p95_latency_ms']}`",
        "",
        "## Buckets",
        ]
    )

    for bucket, bucket_summary in summary["bucket_summaries"].items():
        lines.extend(
            [
                f"### {bucket}",
                f"- cases: `{bucket_summary['cases']}`",
                f"- passed: `{bucket_summary['passed']}`",
                f"- pass_rate: `{bucket_summary['pass_rate']}`",
                f"- avg_weighted_score: `{bucket_summary['avg_weighted_score']}`",
                f"- avg_latency_ms: `{bucket_summary['avg_latency_ms']}`",
                f"- p95_latency_ms: `{bucket_summary['p95_latency_ms']}`",
            ]
        )

    lines.extend(["", "## Case Results"])
    for result in payload["results"]:
        answer_preview = str(result["answer_preview"]).replace("`", "'")
        lines.extend(
            [
                f"### {result['id']} ({result['bucket']})",
                f"- pass: `{result['pass']}`",
                f"- status: `{result['status']}`",
                f"- request_mode: `{result['request_mode']}`",
                f"- expected_route_keys: `{', '.join(result['expected_route_keys']) or '-'}`",
                f"- actual_route_keys: `{', '.join(result['actual_route_keys']) or '-'}`",
                f"- route_pass: `{result['route_pass']}`",
                f"- weighted_score: `{result['weighted_score']}`",
                f"- latency_ms: `{result['latency_ms']}`",
                f"- required_hits: `{len(result['required_hits'])}/{result['required_total']}`",
                f"- must_include_any_hits: `{len(result['must_include_any_hits'])}/{result['must_include_any_total']}`",
                f"- forbidden_hits: `{', '.join(result['forbidden_hits']) or '-'}`",
                f"- answer_preview: `{answer_preview}`",
            ]
        )
        if result.get("error_code"):
            lines.append(f"- error: `{result['error_code']}` / `{result.get('error_message') or '-'}`")

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate /query answer quality against answer-level fixtures.")
    parser.add_argument("--backend", choices=["vector_query", "graph_snapshot"], default=DEFAULT_BACKEND)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--eval-file", type=Path, default=DEFAULT_EVAL_FILE)
    parser.add_argument("--bucket", action="append", default=[])
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--llm-provider", default="lmstudio")
    parser.add_argument("--llm-model", default=None)
    parser.add_argument("--llm-base-url", default=None)
    parser.add_argument("--llm-api-key", default=None)
    parser.add_argument("--graph-collection", default=DEFAULT_COLLECTION_KEY)
    parser.add_argument("--graph-max-hops", type=int, default=2)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-report", type=Path, default=DEFAULT_OUTPUT_REPORT)
    return parser.parse_args()


def run_evaluation(
    *,
    backend: str = DEFAULT_BACKEND,
    base_url: str = DEFAULT_BASE_URL,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    eval_file: Path = DEFAULT_EVAL_FILE,
    buckets: set[str] | None = None,
    case_ids: set[str] | None = None,
    max_cases: int | None = None,
    llm_provider: str = "lmstudio",
    llm_model: str | None = None,
    llm_base_url: str | None = None,
    llm_api_key: str | None = None,
    graph_collection: str = DEFAULT_COLLECTION_KEY,
    graph_max_hops: int = 2,
) -> dict[str, object]:
    resolved_eval_file = (ROOT_DIR / eval_file).resolve() if not eval_file.is_absolute() else eval_file
    fixtures = load_eval_fixtures(
        resolved_eval_file,
        buckets=buckets,
        case_ids=case_ids,
        max_cases=max_cases,
    )
    snapshot = None
    if backend == "vector_query":
        health = health_check(base_url, timeout_seconds)
        collections_payload = collections_check(base_url, timeout_seconds)
        validate_fixture_collections_available(fixtures, collections_payload)
    else:
        collections_payload = None
        snapshot = graphrag_poc_service.build_graph_snapshot(collection_key=graph_collection)
        health = build_graph_snapshot_health(
            snapshot,
            collection_key=graph_collection,
            max_hops=graph_max_hops,
        )

    results: list[dict[str, object]] = []
    for index, case in enumerate(fixtures, start=1):
        if backend == "vector_query":
            payload, expected_route_keys, request_mode = build_query_payload(
                case,
                llm_provider=llm_provider,
                llm_model=llm_model,
                llm_base_url=llm_base_url,
                llm_api_key=llm_api_key,
            )
            request_id = f"answer-eval-{index:03d}-{case['id']}"
            status, body, latency_ms, headers = call_query(
                base_url=base_url,
                timeout_seconds=timeout_seconds,
                request_id=request_id,
                payload=payload,
            )
        else:
            payload, expected_route_keys, request_mode = prepare_query_request_for_backend(
                case,
                max_collection_keys=GRAPH_SNAPSHOT_MAX_COLLECTIONS,
            )
            filtered_snapshot = graphrag_poc_service.filter_graph_snapshot(snapshot or {}, expected_route_keys)
            status, body, latency_ms, headers = call_graph_snapshot(
                snapshot=filtered_snapshot,
                question=str(payload["query"]),
                route_keys=expected_route_keys,
                max_hops=graph_max_hops,
            )
        results.append(
            evaluate_case_result(
                case,
                status=status,
                body=body,
                headers=headers,
                latency_ms=latency_ms,
                expected_route_keys=expected_route_keys,
                request_mode=request_mode,
            )
        )

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "backend": backend,
        "eval_file": str(eval_file),
        "base_url": base_url,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "health": health,
        "collections": collections_payload,
        "summary": summarize_results(results),
        "results": results,
    }


def write_outputs(payload: dict[str, object], *, output_json: Path, output_report: Path) -> None:
    output_json = (ROOT_DIR / output_json).resolve() if not output_json.is_absolute() else output_json
    output_report = (ROOT_DIR / output_report).resolve() if not output_report.is_absolute() else output_report
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_report.write_text(build_markdown_report(payload), encoding="utf-8")


def main() -> None:
    args = parse_args()
    payload = run_evaluation(
        backend=args.backend,
        base_url=args.base_url,
        timeout_seconds=args.timeout_seconds,
        eval_file=args.eval_file,
        buckets={item.strip() for item in args.bucket if item.strip()} or None,
        case_ids={item.strip() for item in args.case_id if item.strip()} or None,
        max_cases=args.max_cases,
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        llm_base_url=args.llm_base_url,
        llm_api_key=args.llm_api_key,
        graph_collection=args.graph_collection,
        graph_max_hops=args.graph_max_hops,
    )

    write_outputs(payload, output_json=args.output_json, output_report=args.output_report)
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
