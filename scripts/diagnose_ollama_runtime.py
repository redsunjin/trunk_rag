from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.1:8b"
DEFAULT_PROMPT = "다음 문장을 그대로 한 번만 출력하세요: 확인"
DEFAULT_REPEAT = 3
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_TEMPERATURE = 0.0


def duration_ns_to_ms(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value) / 1_000_000.0, 3)
    except (TypeError, ValueError):
        return None


def safe_tokens_per_second(token_count: Any, duration_ns: Any) -> float | None:
    try:
        tokens = float(token_count)
        duration = float(duration_ns)
    except (TypeError, ValueError):
        return None
    if tokens <= 0 or duration <= 0:
        return None
    return round(tokens / (duration / 1_000_000_000.0), 3)


def percentile(values: list[float], ratio: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(float(ordered[0]), 3)
    position = (len(ordered) - 1) * ratio
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    if low == high:
        return round(float(ordered[low]), 3)
    fraction = position - low
    return round(float(ordered[low] + (ordered[high] - ordered[low]) * fraction), 3)


def call_ollama_chat(
    *,
    base_url: str,
    model: str,
    prompt: str,
    timeout_seconds: int,
    temperature: float,
    num_predict: int | None,
) -> tuple[dict[str, Any], float]:
    options: dict[str, Any] = {"temperature": temperature}
    if num_predict is not None:
        options["num_predict"] = num_predict

    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": options,
    }
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    started_at = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        elapsed_ms = round((time.perf_counter() - started_at) * 1000.0, 3)
        return {
            "ok": False,
            "error": f"http_error:{exc.code}",
            "detail": detail,
        }, elapsed_ms
    except urllib.error.URLError as exc:
        elapsed_ms = round((time.perf_counter() - started_at) * 1000.0, 3)
        return {
            "ok": False,
            "error": "connection_failed",
            "detail": str(exc),
        }, elapsed_ms

    elapsed_ms = round((time.perf_counter() - started_at) * 1000.0, 3)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "error": "invalid_json",
            "detail": raw,
        }, elapsed_ms

    return payload, elapsed_ms


def normalize_run(payload: dict[str, Any], wall_ms: float, index: int) -> dict[str, Any]:
    message = payload.get("message", {}) if isinstance(payload.get("message"), dict) else {}
    content = str(message.get("content") or "").strip()
    prompt_eval_count = payload.get("prompt_eval_count")
    prompt_eval_duration = payload.get("prompt_eval_duration")
    eval_count = payload.get("eval_count")
    eval_duration = payload.get("eval_duration")

    ok = bool(payload.get("ok", True)) and payload.get("done") is not False
    run = {
        "run": index,
        "ok": ok,
        "wall_ms": wall_ms,
        "load_ms": duration_ns_to_ms(payload.get("load_duration")),
        "total_ms": duration_ns_to_ms(payload.get("total_duration")),
        "prompt_eval_count": prompt_eval_count,
        "prompt_eval_ms": duration_ns_to_ms(prompt_eval_duration),
        "prompt_tokens_per_second": safe_tokens_per_second(prompt_eval_count, prompt_eval_duration),
        "eval_count": eval_count,
        "eval_ms": duration_ns_to_ms(eval_duration),
        "eval_tokens_per_second": safe_tokens_per_second(eval_count, eval_duration),
        "response_chars": len(content),
        "response_preview": content[:120],
    }
    if not ok:
        run["error"] = payload.get("error") or "unknown_error"
        run["detail"] = payload.get("detail")
    return run


def build_assessment(summary: dict[str, Any]) -> dict[str, str]:
    success_count = int(summary.get("success_count") or 0)
    avg_eval_tps = summary.get("avg_eval_tokens_per_second")
    avg_wall_ms = summary.get("avg_wall_ms")

    if success_count == 0:
        return {
            "status": "blocked",
            "message": "직접 Ollama 호출이 실패했습니다.",
            "recommendation": "모델 로드 상태, base URL, Ollama 런타임 자체를 먼저 점검하세요.",
        }

    if avg_eval_tps is None:
        return {
            "status": "unknown",
            "message": "생성 토큰 처리량을 계산할 수 없었습니다.",
            "recommendation": "응답 메타데이터가 있는 모델로 다시 측정하거나 raw payload를 확인하세요.",
        }

    if avg_eval_tps >= 20 and (avg_wall_ms or 0) <= 5000:
        return {
            "status": "promising",
            "message": "직접 생성 처리량은 양호한 편입니다.",
            "recommendation": "RAG 경로에서도 병목이 남으면 prompt/context 또는 retrieval 쪽을 추가 진단하세요.",
        }

    if avg_eval_tps >= 8 and (avg_wall_ms or 0) <= 15000:
        return {
            "status": "borderline",
            "message": "직접 생성 처리량은 경계선 수준입니다.",
            "recommendation": "짧은 context나 낮은 출력 길이에서는 가능하지만 trunk_rag 기본 RAG 질의에서는 느릴 수 있습니다.",
        }

    return {
        "status": "slow",
        "message": "직접 생성 처리량이 낮아 context-heavy RAG에서 timeout 가능성이 큽니다.",
        "recommendation": "검증된 `llama3.1:8b + timeout 30초` 또는 클라우드 추론 경로를 우선 사용하세요.",
    }


def summarize_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    success_runs = [run for run in runs if run.get("ok")]
    wall_values = [float(run["wall_ms"]) for run in success_runs if run.get("wall_ms") is not None]
    eval_tps_values = [
        float(run["eval_tokens_per_second"])
        for run in success_runs
        if run.get("eval_tokens_per_second") is not None
    ]
    prompt_tps_values = [
        float(run["prompt_tokens_per_second"])
        for run in success_runs
        if run.get("prompt_tokens_per_second") is not None
    ]

    summary = {
        "runs": len(runs),
        "success_count": len(success_runs),
        "failure_count": len(runs) - len(success_runs),
        "avg_wall_ms": round(statistics.mean(wall_values), 3) if wall_values else None,
        "p95_wall_ms": percentile(wall_values, 0.95),
        "avg_eval_tokens_per_second": round(statistics.mean(eval_tps_values), 3) if eval_tps_values else None,
        "avg_prompt_tokens_per_second": round(statistics.mean(prompt_tps_values), 3) if prompt_tps_values else None,
    }
    summary["assessment"] = build_assessment(summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose direct Ollama runtime throughput.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--repeat", type=int, default=DEFAULT_REPEAT)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--num-predict", type=int)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def print_human_readable(report: dict[str, Any]) -> None:
    print("[ollama-runtime]")
    print(f"  model={report['model']}")
    print(f"  base_url={report['base_url']}")
    assessment = report["summary"]["assessment"]
    print(f"  assessment={assessment['status']} - {assessment['message']}")
    print(f"  next={assessment['recommendation']}")
    for run in report["runs"]:
        status = "ok" if run["ok"] else "fail"
        print(
            f"- run={run['run']} {status} wall_ms={run['wall_ms']} "
            f"eval_tps={run.get('eval_tokens_per_second')} "
            f"prompt_tps={run.get('prompt_tokens_per_second')} "
            f"response_chars={run.get('response_chars')}"
        )
        if not run["ok"]:
            print(f"  error={run.get('error')} detail={run.get('detail')}")


def main() -> int:
    args = parse_args()
    if args.repeat < 1:
        raise ValueError("--repeat must be >= 1")
    if args.timeout_seconds < 1:
        raise ValueError("--timeout-seconds must be >= 1")

    runs: list[dict[str, Any]] = []
    for index in range(1, args.repeat + 1):
        payload, wall_ms = call_ollama_chat(
            base_url=args.base_url,
            model=args.model,
            prompt=args.prompt,
            timeout_seconds=args.timeout_seconds,
            temperature=args.temperature,
            num_predict=args.num_predict,
        )
        runs.append(normalize_run(payload, wall_ms, index))

    report = {
        "model": args.model,
        "base_url": args.base_url,
        "prompt": args.prompt,
        "repeat": args.repeat,
        "runs": runs,
        "summary": summarize_runs(runs),
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human_readable(report)

    assessment_status = report["summary"]["assessment"]["status"]
    return 0 if assessment_status in {"promising", "borderline"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
