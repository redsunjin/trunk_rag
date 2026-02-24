# PREPROCESSING PROMPT TEMPLATE (P1)

목적:
- 외부 전처리 담당자가 동일한 규칙으로 RAG용 Markdown을 생성하도록 한다.
- `trunk_rag` 등록 검증(`usable`) 기준과 호환되도록 결과를 유도한다.

## 사용 방법

1. 원본 텍스트를 아래 프롬프트의 `[INPUT]`에 넣는다.
2. 출력은 반드시 2개 산출물로 받는다.
- `document_md`: RAG 인덱싱용 Markdown
- `metadata_json`: `docs/PREPROCESSING_METADATA_SCHEMA.json` 호환 JSON
3. 생성 후 `scripts/validate_rag_doc.py`로 검증한다.

## Prompt Template

```text
당신은 RAG 인덱싱용 문서 전처리기입니다.
아래 제약을 반드시 지키세요.

[목표]
- 입력 원문을 RAG 친화 Markdown으로 정리
- 정보 손실 최소화
- 사실관계 변경 금지

[출력 형식]
아래 두 블록을 순서대로 출력:
1) document_md (Markdown)
2) metadata_json (JSON)

[document_md 규칙]
- 허용 헤더: ##, ###, ####
- 문서에는 최소 1개 이상의 ## 섹션 포함
- 각 섹션 본문은 20자 이상 권장
- 빈 섹션 금지
- 중복 제목 최소화
- 불필요한 장식/이모지 제거
- 핵심 수치/고유명사는 원문 기준 유지

[metadata_json 규칙]
- 필수 필드:
  - source (파일명)
  - country (all|france|germany|italy|uk)
  - doc_type (summary|country)
- 선택 필드:
  - preprocess_version
  - processed_at (ISO8601)
  - source_license
  - language (기본 "ko")
  - tags (문자열 배열)

[금지]
- 근거 없는 추론/창작
- 원문 의미 왜곡
- JSON 주석

[INPUT]
{{RAW_TEXT}}
```

## 산출물 예시

`document_md`:

```md
## 절대왕정과 과학 정책
루이 14세 시기 과학 정책은 국가 권력 강화와 결합되었다.

### 마를리 기계
대규모 양수 설비를 통해 기술력과 왕권 상징을 동시에 확보했다.
```

`metadata_json`:

```json
{
  "source": "fr.md",
  "country": "france",
  "doc_type": "country",
  "preprocess_version": "v1",
  "processed_at": "2026-02-24T00:00:00Z",
  "source_license": "internal",
  "language": "ko",
  "tags": ["france", "science-history"]
}
```

