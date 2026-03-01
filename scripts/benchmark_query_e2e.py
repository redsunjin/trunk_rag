from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_SECONDS = 45
DEFAULT_QUERY_TIMEOUT_SECONDS = 60
DEFAULT_ROUNDS = 3
MAX_ERROR_SAMPLES = 10
DEFAULT_SCENARIOS: dict[str, list[str]] = {
    "single_all": ["all"],
    "single_fr": ["fr"],
    "dual_fr_ge": ["fr", "ge"],
}
DEFAULT_QUERIES = [
    "프랑스의 대표적인 과학 혁신 사례를 요약해줘",
    "독일의 과학 발전 특징을 간단히 정리해줘",
    "프랑스와 독일의 공통 과학적 성과를 비교해줘",
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


def parse_collection_keys(raw: str, *, max_collections: int = 2) -> list[str]:
    keys = [item.strip().lower() for item in raw.split(",") if item.strip()]
    deduped: list[str] = []
    seen: set[str] = set()
    for key in keys:
        if key in seen:
            continue
        seen.add(key)
        deduped.append(key)
    if not deduped:
        raise ValueError(f"Invalid scenario collection keys: {raw}")
    if len(deduped) > max_collections:
        raise ValueError(f"Up to {max_collections} collections are supported: {raw}")
    return deduped


def build_scenarios(raw_specs: list[str] | None) -> dict[str, list[str]]:
    if not raw_specs:
        return DEFAULT_SCENARIOS

    scenarios: dict[str, list[str]] = {}
    for raw in raw_specs:
        keys = parse_collection_keys(raw)
        name = "custom_" + "_".join(keys)
        scenarios[name] = keys
    return scenarios


def health_check(base_url: str, timeout_seconds: int) -> dict[str, object]:
    request = urllib.request.Request(f"{base_url}/health", method="GET")
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        payload = response.read()
    return json.loads(payload.decode("utf-8"))


def call_query(
    *,
    base_url: str,
    timeout_seconds: int,
    request_id: str,
    payload: dict[str, object],
) -> tuple[int, dict[str, object], float]:
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

    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            return response.status, json.loads(raw), elapsed_ms
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        try:
            body_json = json.loads(raw) if raw else {}
        except Exception:
            body_json = {"raw": raw}
        return int(exc.code), body_json, elapsed_ms
    except urllib.error.URLError as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return 0, {"error": str(exc)}, elapsed_ms


def run_scenario(
    *,
    scenario_name: str,
    collection_keys: list[str],
    queries: list[str],
    rounds: int,
    base_url: str,
    query_timeout_seconds: int,
    llm_provider: str,
    llm_model: str | None,
    llm_base_url: str | None,
    llm_api_key: str | None,
    inter_request_sleep_ms: int,
) -> dict[str, object]:
    latencies_success: list[float] = []
    latencies_all: list[float] = []
    status_counts: dict[int, int] = {}
    error_samples: list[dict[str, object]] = []

    total_requests = rounds * len(queries)
    request_index = 0
    for round_index in range(rounds):
        for query in queries:
            request_index += 1
            payload: dict[str, object] = {
                "query": query,
                "llm_provider": llm_provider,
            }
            if llm_model:
                payload["llm_model"] = llm_model
            if llm_base_url:
                payload["llm_base_url"] = llm_base_url
            if llm_api_key:
                payload["llm_api_key"] = llm_api_key

            if len(collection_keys) == 1:
                payload["collection"] = collection_keys[0]
            else:
                payload["collection"] = collection_keys[0]
                payload["collections"] = collection_keys

            request_id = f"bench-{scenario_name}-{round_index + 1}-{request_index}"
            status, response_body, elapsed_ms = call_query(
                base_url=base_url,
                timeout_seconds=query_timeout_seconds,
                request_id=request_id,
                payload=payload,
            )

            latencies_all.append(elapsed_ms)
            status_counts[status] = status_counts.get(status, 0) + 1
            if 200 <= status < 300:
                latencies_success.append(elapsed_ms)
            elif len(error_samples) < MAX_ERROR_SAMPLES:
                error_samples.append(
                    {
                        "status": status,
                        "request_id": request_id,
                        "query": query,
                        "response": response_body,
                    }
                )

            if inter_request_sleep_ms > 0:
                time.sleep(inter_request_sleep_ms / 1000.0)

    success_count = len(latencies_success)
    failure_count = total_requests - success_count

    return {
        "name": scenario_name,
        "collection_keys": collection_keys,
        "measurements": total_requests,
        "success_count": success_count,
        "failure_count": failure_count,
        "success_ratio": round((success_count / total_requests), 4) if total_requests else 0.0,
        "status_counts": status_counts,
        "latency_all_avg_ms": round(mean(latencies_all), 3) if latencies_all else 0.0,
        "latency_all_p95_ms": round(percentile(latencies_all, 0.95), 3),
        "latency_success_avg_ms": round(mean(latencies_success), 3) if latencies_success else None,
        "latency_success_p50_ms": round(percentile(latencies_success, 0.5), 3)
        if latencies_success
        else None,
        "latency_success_p95_ms": round(percentile(latencies_success, 0.95), 3)
        if latencies_success
        else None,
        "errors_sample": error_samples,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark /query end-to-end latency (including LLM generation)."
    )
    parser.add_argument("--base-url", type=str, default=DEFAULT_BASE_URL)
    parser.add_argument("--scenario", action="append", help="Collection keys, example: fr,ge")
    parser.add_argument("--query", action="append", help="Custom query. Can be repeated.")
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    parser.add_argument("--llm-provider", type=str, default="ollama")
    parser.add_argument("--llm-model", type=str)
    parser.add_argument("--llm-base-url", type=str)
    parser.add_argument("--llm-api-key", type=str)
    parser.add_argument("--health-timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--query-timeout-seconds", type=int, default=DEFAULT_QUERY_TIMEOUT_SECONDS)
    parser.add_argument("--skip-health-check", action="store_true")
    parser.add_argument("--warmup", type=int, default=1, help="Warmup calls per scenario.")
    parser.add_argument("--inter-request-sleep-ms", type=int, default=0)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.rounds < 1:
        raise ValueError("--rounds must be >= 1")
    if args.warmup < 0:
        raise ValueError("--warmup must be >= 0")

    base_url = args.base_url.rstrip("/")
    scenarios = build_scenarios(args.scenario)
    queries = args.query if args.query else DEFAULT_QUERIES

    health: dict[str, object] | None = None
    if not args.skip_health_check:
        health = health_check(base_url, args.health_timeout_seconds)

    results: list[dict[str, object]] = []
    for name, keys in scenarios.items():
        if args.warmup > 0:
            run_scenario(
                scenario_name=f"{name}_warmup",
                collection_keys=keys,
                queries=queries[:1],
                rounds=args.warmup,
                base_url=base_url,
                query_timeout_seconds=args.query_timeout_seconds,
                llm_provider=args.llm_provider,
                llm_model=args.llm_model,
                llm_base_url=args.llm_base_url,
                llm_api_key=args.llm_api_key,
                inter_request_sleep_ms=0,
            )

        result = run_scenario(
            scenario_name=name,
            collection_keys=keys,
            queries=queries,
            rounds=args.rounds,
            base_url=base_url,
            query_timeout_seconds=args.query_timeout_seconds,
            llm_provider=args.llm_provider,
            llm_model=args.llm_model,
            llm_base_url=args.llm_base_url,
            llm_api_key=args.llm_api_key,
            inter_request_sleep_ms=args.inter_request_sleep_ms,
        )
        results.append(result)

    payload = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "base_url": base_url,
        "rounds": args.rounds,
        "warmup": args.warmup,
        "queries": queries,
        "llm": {
            "provider": args.llm_provider,
            "model": args.llm_model,
            "base_url": args.llm_base_url,
        },
        "health": health,
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
