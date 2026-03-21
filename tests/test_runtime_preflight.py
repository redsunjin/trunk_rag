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
