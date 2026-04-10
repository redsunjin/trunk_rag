from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def _read_doc(path: str) -> str:
    return (ROOT_DIR / path).read_text(encoding="utf-8")


def test_upload_examples_separate_core_and_sample_pack_paths():
    readme = _read_doc("README.md")
    spec = _read_doc("SPEC.md")

    assert "업로드 요청 생성 예시(core 기본 경로)" in readme
    assert '\\"collection\\":\\"all\\"' in readme
    assert "sample-pack compatibility 컬렉션에 직접 올리는 예시는 별도 호환 경로로만 사용합니다." in readme
    assert '\\"collection\\":\\"fr\\"' in readme

    assert "요청(core 기본 경로)" in spec
    assert '"collection": "all"' in spec
    assert "sample-pack compatibility 컬렉션에 직접 올리는 경우에만" in spec
    assert "`collection=fr`, `country=france`, `doc_type=country`" in spec


def test_preprocessing_docs_label_sample_pack_metadata_examples():
    rules = _read_doc("docs/PREPROCESSING_RULES.md")
    prompt_template = _read_doc("docs/PREPROCESSING_PROMPT_TEMPLATE.md")

    assert "core 기본 샘플 입력" in rules
    assert '"country": "all"' in rules
    assert '"doc_type": "summary"' in rules
    assert "sample-pack compatibility 샘플 입력" in rules
    assert '"country": "france"' in rules
    assert "COUNTRY_BY_STEM" not in rules

    assert "core 기본 `metadata_json`" in prompt_template
    assert '"country": "all"' in prompt_template
    assert "sample-pack compatibility `metadata_json`" in prompt_template
    assert '"country": "france"' in prompt_template
    assert "country (all|france|germany|italy|uk)" not in prompt_template


def test_docs_describe_bundled_seed_corpus_as_demo_bootstrap_data():
    readme = _read_doc("README.md")
    spec = _read_doc("SPEC.md")

    assert "sample-pack demo/bootstrap corpus" in readme
    assert "제품 본체 도메인 데이터가 아닙니다" in readme
    assert "첫 실행 확인용 sample-pack demo/bootstrap corpus" in spec
    assert "seed_corpus_*" in spec
    assert "제품 본체 도메인 데이터가 아님" in spec
