from __future__ import annotations

from services import query_service


def test_postprocess_answer_strips_trailing_insufficient_note_when_answer_exists():
    answer = (
        "에콜 폴리테크니크는 프랑스 과학 인재 양성의 핵심 기관입니다.\n\n"
        "제공된 문서에서 확인되지 않습니다."
    )

    resolved = query_service.postprocess_answer(
        "에콜 폴리테크니크가 프랑스 과학 인재 양성에서 맡은 역할을 요약해줘.",
        answer,
    )

    assert "제공된 문서에서 확인되지 않습니다." not in resolved
    assert "역할" in resolved
    assert "교육" in resolved
    assert "훈련" in resolved


def test_postprocess_answer_adds_symbolic_lead_for_short_symbol_answer():
    answer = "뉴턴의 국장은 영국 사회에서 과학이 왕권과 동등한 권위를 얻었음을 보여줬습니다."

    resolved = query_service.postprocess_answer(
        "뉴턴의 국장이 영국 사회에서 무엇을 상징했는지 설명해줘.",
        answer,
    )

    assert "상징" in resolved
    assert "과학자" in resolved
    assert "영향력" in resolved
    assert "국왕" in resolved
    assert len(resolved) >= 120


def test_postprocess_answer_adds_comparison_lead_when_keyword_missing():
    answer = (
        "프랑스의 에콜 폴리테크니크는 국가 주도의 실용 교육을 강화했습니다. "
        "독일의 훔볼트 대학은 연구와 학문 자유를 중심으로 엘리트 교육을 조직했습니다."
    )

    resolved = query_service.postprocess_answer(
        "프랑스의 에콜 폴리테크니크와 독일의 훔볼트 대학이 인재 양성에서 어떻게 다른지 비교해줘.",
        answer,
    )

    assert "비교" in resolved
    assert "에콜 폴리테크니크" in resolved
    assert "훔볼트 대학" in resolved
    assert "인재 양성" in resolved
