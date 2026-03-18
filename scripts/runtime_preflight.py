from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from common import load_project_env
from services import runtime_service

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


def normalize_hf_cache_dir(model_name: str) -> str:
    return "models--" + model_name.replace("/", "--")


def candidate_hf_cache_roots(home: Path | None = None) -> list[Path]:
    base_home = home or Path.home()
    roots: list[Path] = []

    hub_cache = os.getenv("HUGGINGFACE_HUB_CACHE")
    if hub_cache:
        roots.append(Path(hub_cache).expanduser())

    hf_home = os.getenv("HF_HOME")
    if hf_home:
        roots.append(Path(hf_home).expanduser() / "hub")

    roots.extend(
        [
            base_home / ".cache" / "huggingface" / "hub",
            base_home / "Library" / "Caches" / "huggingface" / "hub",
        ]
    )

    deduped: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(root)
    return deduped


def is_hf_cache_model_ready(cache_dir: Path) -> bool:
    snapshots_dir = cache_dir / "snapshots"
    if not snapshots_dir.exists():
        return False

    # Partial HuggingFace downloads leave `.incomplete` blobs behind. Treat them
    # as not ready so runtime preflight does not pass on broken local caches.
    incomplete_files = list((cache_dir / "blobs").glob("*.incomplete"))
    if incomplete_files:
        return False

    for snapshot in snapshots_dir.iterdir():
        if not snapshot.is_dir():
            continue
        if any(
            (snapshot / file_name).exists()
            for file_name in ("model.safetensors", "pytorch_model.bin", "model.safetensors.index.json")
        ):
            return True
    return False


def find_local_embedding_model(model_name: str, roots: list[Path] | None = None) -> Path | None:
    direct_path = Path(model_name).expanduser()
    if direct_path.exists():
        return direct_path.resolve()

    cache_dir_name = normalize_hf_cache_dir(model_name)
    for root in roots or candidate_hf_cache_roots():
        candidate = root / cache_dir_name
        if candidate.exists() and is_hf_cache_model_ready(candidate):
            return candidate.resolve()
    return None


def fetch_json(url: str, timeout_seconds: int) -> dict[str, Any]:
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        payload = response.read()
    return json.loads(payload.decode("utf-8"))


def validate_health_payload(payload: dict[str, object]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_HEALTH_KEYS - payload.keys())
    if missing:
        errors.append(
            "Unexpected /health payload. "
            f"Missing fields: {', '.join(missing)}. "
            "다른 프로젝트가 같은 포트를 사용 중인지 확인하세요."
        )
    if payload.get("status") != "ok":
        errors.append(f"Unexpected /health status: {payload.get('status')}")
    return errors


def check_embedding_model(model_name: str, roots: list[Path] | None = None) -> dict[str, object]:
    local_path = find_local_embedding_model(model_name, roots=roots)
    ready = local_path is not None
    if ready:
        message = f"local model cache/path detected: {local_path}"
    else:
        message = (
            "local embedding model not found. "
            "DOC_RAG_EMBEDDING_MODEL로 로컬 경로를 지정하거나 HuggingFace cache를 준비하세요."
        )
    return {
        "name": "embedding_model",
        "critical": True,
        "ready": ready,
        "target": model_name,
        "detected_path": str(local_path) if local_path else None,
        "message": message,
    }


def check_app_health(base_url: str, timeout_seconds: int) -> dict[str, object]:
    target = f"{base_url.rstrip('/')}/health"
    try:
        payload = fetch_json(target, timeout_seconds)
    except urllib.error.URLError as exc:
        return {
            "name": "app_health",
            "critical": True,
            "ready": False,
            "target": target,
            "message": f"health endpoint unreachable: {exc}",
        }
    except Exception as exc:
        return {
            "name": "app_health",
            "critical": True,
            "ready": False,
            "target": target,
            "message": f"health check failed: {exc}",
        }

    errors = validate_health_payload(payload)
    vectors = payload.get("vectors")
    if isinstance(vectors, int) and vectors < 1:
        errors.append("vectors=0 입니다. 벤치 전에 Reindex가 필요합니다.")

    ready = not errors
    message = "ready" if ready else " / ".join(errors)
    return {
        "name": "app_health",
        "critical": True,
        "ready": ready,
        "target": target,
        "payload": payload,
        "message": message,
    }


def check_ollama(base_url: str, model_name: str | None, timeout_seconds: int) -> dict[str, object]:
    target = f"{base_url.rstrip('/')}/api/tags"
    try:
        payload = fetch_json(target, timeout_seconds)
    except urllib.error.URLError as exc:
        return {
            "name": "ollama",
            "critical": True,
            "ready": False,
            "target": target,
            "message": f"ollama endpoint unreachable: {exc}",
        }
    except Exception as exc:
        return {
            "name": "ollama",
            "critical": True,
            "ready": False,
            "target": target,
            "message": f"ollama check failed: {exc}",
        }

    models = payload.get("models", [])
    available = sorted(
        str(item.get("name"))
        for item in models
        if isinstance(item, dict) and item.get("name")
    )
    if model_name and model_name not in available:
        return {
            "name": "ollama",
            "critical": True,
            "ready": False,
            "target": target,
            "available_models": available,
            "message": f"required ollama model is missing: {model_name}",
        }

    return {
        "name": "ollama",
        "critical": True,
        "ready": True,
        "target": target,
        "available_models": available,
        "message": "ready",
    }


def build_report(
    *,
    app_base_url: str,
    timeout_seconds: int,
    llm_provider: str,
    llm_model: str | None,
    llm_base_url: str | None,
    embedding_model: str,
) -> dict[str, object]:
    checks = [
        check_app_health(app_base_url, timeout_seconds),
        check_embedding_model(embedding_model),
    ]

    if llm_provider == "ollama":
        checks.append(check_ollama(llm_base_url or "http://localhost:11434", llm_model, timeout_seconds))

    ready = all(bool(check["ready"]) for check in checks if check.get("critical"))
    return {
        "ready": ready,
        "app_base_url": app_base_url,
        "embedding_model": embedding_model,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "llm_base_url": llm_base_url,
        "checks": checks,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check local runtime readiness before running P1 benchmarks."
    )
    parser.add_argument("--base-url", type=str, default="http://127.0.0.1:8000")
    parser.add_argument("--timeout-seconds", type=int, default=5)
    parser.add_argument("--llm-provider", type=str)
    parser.add_argument("--llm-model", type=str)
    parser.add_argument("--llm-base-url", type=str)
    parser.add_argument("--embedding-model", type=str)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def print_human_readable(report: dict[str, object]) -> None:
    overall = "ready" if report["ready"] else "blocked"
    print(f"[runtime] {overall}")
    print(f"  app_base_url={report['app_base_url']}")
    print(f"  embedding_model={report['embedding_model']}")
    print(f"  llm={report['llm_provider']}:{report['llm_model']}")
    for check in report["checks"]:
        status = "ready" if check["ready"] else "blocked"
        print(f"- {check['name']}: {status} - {check['message']}")


def main() -> int:
    args = parse_args()
    env_path = load_project_env()
    if env_path:
        print(f"Loaded env: {env_path}", file=sys.stderr)

    default_llm = runtime_service.get_default_llm_config()
    report = build_report(
        app_base_url=args.base_url,
        timeout_seconds=args.timeout_seconds,
        llm_provider=(args.llm_provider or str(default_llm["provider"] or "ollama")).strip(),
        llm_model=(args.llm_model or str(default_llm["model"] or "")).strip() or None,
        llm_base_url=(args.llm_base_url or str(default_llm["base_url"] or "")).strip() or None,
        embedding_model=(args.embedding_model or runtime_service.get_embedding_model()).strip(),
    )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human_readable(report)

    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
