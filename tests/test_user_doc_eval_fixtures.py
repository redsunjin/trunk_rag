from __future__ import annotations

import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT_DIR / "evals" / "user_doc_answer_level_eval_fixtures.jsonl"
QUESTION_SET_PATH = ROOT_DIR / "docs" / "USER_DOC_QUERY_EVAL_QUESTION_SET.md"


def test_user_doc_eval_fixture_is_loadable_and_opt_in():
    records = [
        json.loads(line)
        for line in FIXTURE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert [record["id"] for record in records] == ["UDQ-BC-01", "UDQ-BC-02", "UDQ-BC-03"]
    for record in records:
        assert record["bucket"] == "user-doc-candidate"
        assert record["collection_keys"] == ["project_docs"]
        assert record["evaluation"]["source"] == "docs/USER_DOC_QUERY_EVAL_QUESTION_SET.md"
        assert (ROOT_DIR / record["evaluation"]["source"]).exists()
        assert record["query"]
        assert record["evaluation"]["must_include"]
        assert record["evaluation"]["must_not_include"]
    assert FIXTURE_PATH.name != "answer_level_eval_fixtures.jsonl"


def test_user_doc_question_set_lists_every_fixture():
    question_set = QUESTION_SET_PATH.read_text(encoding="utf-8")

    for case_id in ["UDQ-BC-01", "UDQ-BC-02", "UDQ-BC-03"]:
        assert question_set.count(case_id) == 1
