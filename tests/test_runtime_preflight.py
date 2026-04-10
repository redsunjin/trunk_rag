from __future__ import annotations

from pathlib import Path

from scripts import runtime_preflight


def test_find_local_embedding_model_accepts_direct_path(tmp_path: Path):
    model_dir = tmp_path / "local-bge-m3"
    model_dir.mkdir()

    resolved = runtime_preflight.find_local_embedding_model(str(model_dir), roots=[])

    assert resolved == model_dir.resolve()


def test_find_local_embedding_model_uses_hf_cache_layout(tmp_path: Path):
    hub_dir = tmp_path / "hub"
    model_dir = hub_dir / "models--BAAI--bge-m3"
    snapshot_dir = model_dir / "snapshots" / "local"
    snapshot_dir.mkdir(parents=True)
    (snapshot_dir / "model.safetensors").write_text("ok", encoding="utf-8")

    resolved = runtime_preflight.find_local_embedding_model("BAAI/bge-m3", roots=[hub_dir])

    assert resolved == model_dir.resolve()


def test_validate_health_payload_detects_missing_fields():
    errors = runtime_preflight.validate_health_payload({"status": "ok"})

    assert errors
    assert "Missing fields" in errors[0]


def test_check_embedding_model_reports_missing_cache(tmp_path: Path):
    result = runtime_preflight.check_embedding_model("BAAI/bge-m3", roots=[tmp_path / "hub"])

    assert result["name"] == "embedding_model"
    assert result["ready"] is False
    assert "DOC_RAG_EMBEDDING_MODEL" in result["message"]


def test_find_local_embedding_model_rejects_incomplete_hf_cache(tmp_path: Path):
    hub_dir = tmp_path / "hub"
    model_dir = hub_dir / "models--BAAI--bge-m3"
    snapshot_dir = model_dir / "snapshots" / "local"
    snapshot_dir.mkdir(parents=True)
    (snapshot_dir / "config.json").write_text("{}", encoding="utf-8")
    blobs_dir = model_dir / "blobs"
    blobs_dir.mkdir(parents=True)
    (blobs_dir / "partial.incomplete").write_text("partial", encoding="utf-8")

    resolved = runtime_preflight.find_local_embedding_model("BAAI/bge-m3", roots=[hub_dir])

    assert resolved is None


def test_check_lmstudio_reports_missing_model(monkeypatch):
    monkeypatch.setattr(
        runtime_preflight,
        "fetch_json",
        lambda target, timeout_seconds: {"data": [{"id": "loaded-model"}]},
    )

    result = runtime_preflight.check_lmstudio("http://127.0.0.1:1337/v1", "qwen3.5-4b-mlx-4bit", 5)

    assert result["name"] == "lmstudio"
    assert result["ready"] is False
    assert "required lmstudio model is missing" in result["message"]


def test_check_lmstudio_accepts_loaded_model(monkeypatch):
    monkeypatch.setattr(
        runtime_preflight,
        "fetch_json",
        lambda target, timeout_seconds: {"data": [{"id": "qwen3.5-4b-mlx-4bit"}]},
    )

    result = runtime_preflight.check_lmstudio("http://127.0.0.1:1337/v1", "qwen3.5-4b-mlx-4bit", 5)

    assert result["name"] == "lmstudio"
    assert result["ready"] is True


def test_check_runtime_profile_blocks_not_recommended_model():
    result = runtime_preflight.check_runtime_profile("ollama", "qwen3:4b", 30)

    assert result["name"] == "runtime_profile"
    assert result["ready"] is False
    assert result["status"] == "not_recommended"
    assert "gemma4:e4b" in str(result["recommendation"])


def test_check_runtime_profile_accepts_verified_local_model():
    result = runtime_preflight.check_runtime_profile("ollama", "gemma4:e4b", 30)

    assert result["name"] == "runtime_profile"
    assert result["ready"] is True
    assert result["status"] == "verified"


def test_check_app_health_blocks_embedding_fingerprint_mismatch(monkeypatch):
    monkeypatch.setattr(
        runtime_preflight,
        "fetch_json",
        lambda target, timeout_seconds: {
            "status": "ok",
            "collection_key": "all",
            "collection": "w2_007_header_rag",
            "persist_dir": "mock",
            "vectors": 37,
            "chunking_mode": "char",
            "embedding_model": "BAAI/bge-m3",
            "default_llm_provider": "ollama",
            "default_llm_model": "llama3.1:8b",
            "runtime_profile_status": "verified",
            "runtime_profile_message": "ok",
            "runtime_query_budget_profile": "verified_local_single",
            "runtime_query_budget_summary": "profile=verified_local_single",
            "embedding_fingerprint_status": "mismatch",
            "embedding_fingerprint_message": "fingerprint mismatch",
        },
    )

    result = runtime_preflight.check_app_health("http://127.0.0.1:8000", 5)

    assert result["ready"] is False
    assert "fingerprint mismatch" in result["message"]
