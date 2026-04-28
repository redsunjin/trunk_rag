from __future__ import annotations

import json

from services import feedback_service


def test_append_feedback_writes_jsonl(tmp_path, monkeypatch):
    monkeypatch.setattr(feedback_service, "PERSIST_DIR", str(tmp_path))

    saved = feedback_service.append_feedback(
        {
            "request_id": "req-1",
            "query": "테스트 질문",
            "rating": "positive",
            "quality_mode": "balanced",
        }
    )

    path = tmp_path / feedback_service.QUERY_FEEDBACK_STORE_FILE
    assert saved["storage"] == str(path)
    assert path.exists()
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["id"] == saved["id"]
    assert records[0]["request_id"] == "req-1"
    assert records[0]["rating"] == "positive"
