from __future__ import annotations

import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT_DIR / "evals" / "user_doc_answer_level_eval_fixtures.jsonl"


def test_user_doc_eval_fixture_is_loadable_and_opt_in():
    records = [
        json.loads(line)
        for line in FIXTURE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert [record["id"] for record in records] == ["UDQ-BC-01"]
    record = records[0]
    assert record["bucket"] == "user-doc-candidate"
    assert record["collection_keys"] == ["project_docs"]
    assert record["evaluation"]["source"] == "docs/USER_DOC_QUERY_EVAL_QUESTION_SET.md"
    assert (ROOT_DIR / record["evaluation"]["source"]).exists()
    assert FIXTURE_PATH.name != "answer_level_eval_fixtures.jsonl"
