# doc_rag Roadmap & Dev Dashboard (2026-03-01 기준)

<!-- ROADMAP_DASHBOARD_START -->
| Metric | Value |
|---|---|
| Last Updated (KST) | 2026-03-03 12:00:29 |
| Branch / HEAD | `main` / `0aad505` |
| Working Tree | dirty |
| TODO Progress | 48/87 (55.2%) |
| Immediate Track | 4/7 (57.1%) |
| Conditional Track | 0/7 (0.0%) |
<!-- ROADMAP_DASHBOARD_END -->

## 1) 사용 규칙 (중요)

이 문서를 개발진행 대시보드로 사용한다.

문서/체크박스 업데이트 시 반드시 아래를 실행:

```powershell
.venv\Scripts\python.exe scripts\update_roadmap_dashboard.py
```

업데이트 기준:
1. `TODO.md` 체크박스 변동
2. `NEXT_SESSION_PLAN.md`의 `[Immediate]`, `[Conditional]` 체크박스 변동
3. 주요 계획 문서(`README.md`, `SPEC.md`, `docs/reports/*`) 수정

참조 문서:
- `TODO.md`
- `docs/NEXT_SESSION_CONTEXT_2026-02-28.md`
- `docs/reports/CODEBASE_EFFICIENCY_REVIEW_2026-02-28.md`
- `W3_006_RAG_기술경험_참고문서.md`

## 2) 현재 상태 요약

완료 상태:
1. P3-Prep(백엔드/프론트/테스트 분해) 완료
2. `app_api.py` 조립 계층화 및 라우트/서비스 분리 완료
3. 회귀 테스트 `24 passed`

현재 초점:
1. W3_006 적용안 중 즉시적용 항목을 본 개발로 반영
2. 조건부 적용 항목은 PoC 게이트를 통과한 뒤 본 반영

## 3) W3_006 적용 로드맵

### 3-1) 즉시적용 Track (본 개발 반영)

목표:
- 저위험/고효과 항목을 즉시 운영 가능한 형태로 반영한다.

작업 항목:
- [x] `[Immediate]` `/query` 검색 추적 로그 저장(질문, 라우팅, top-k 요약, request_id)
- [x] `[Immediate]` 응답 스키마에 citation 필드 추가(`sources[]` 또는 동등 구조)
- [x] `[Immediate]` 문서 메타데이터 스키마 확장(`year_text`, `scientist`, `source_file`, `topic` 호환)
- [x] `[Immediate]` 업로드/인덱싱 검증에 신규 메타 필드 optional 규칙 추가
- [x] `[Immediate]` 오답노트용 실패 케이스 수집 포맷(JSON) 도입
- [x] `[Immediate]` API/프론트 테스트에 citation/로그 계약 검증 케이스 추가
- [x] `[Immediate]` 운영 문서(`README.md`, `SPEC.md`, `TODO.md`) 동기화

완료 기준:
1. API 계약 변경사항이 테스트로 고정됨
2. 로그/근거 데이터로 사후 분석이 가능함
3. 기존 기능 회귀(`pytest -q`) 통과

### 3-2) 조건부적용 Track (PoC 게이트 후 반영)

목표:
- 정확도 개선 효과가 검증된 항목만 본 라인에 채택한다.

작업 항목:
- [ ] `[Conditional]` fact 질문 deterministic 경로 PoC 구현
- [ ] `[Conditional]` 멀티쿼리 확장(질의 rewrite) PoC
- [ ] `[Conditional]` 키워드 보강 검색 PoC
- [ ] `[Conditional]` grounded/sufficient 품질 게이트 + 1회 재시도 PoC
- [ ] `[Conditional]` BM25+Vector 하이브리드 검색 PoC
- [ ] `[Conditional]` cross-encoder reranker PoC
- [ ] `[Conditional]` PoC별 p50/p95 및 정답률 비교 리포트 작성

채택 게이트:
1. 정답률/근거정합 지표 개선이 baseline 대비 유의미
2. `/query` p95 악화가 운영 허용치 이내
3. 복잡도 대비 운영 이점이 명확

## 4) 실행 순서 (2 Sprint)

### Sprint-1 (2026-03-02 ~ 2026-03-08)

1. 즉시적용 Track 우선 구현
2. 회귀 테스트/문서 동기화
3. baseline 측정값 고정(정확도/지연)

### Sprint-2 (2026-03-09 ~ 2026-03-15)

1. 조건부적용 PoC 1차(Deterministic + 멀티쿼리 + 품질게이트)
2. 하이브리드/reranker는 비용 대비 효과 검토 후 착수 여부 결정
3. 채택/보류 결론과 근거 리포트 확정

## 5) Dashboard 운영 메모

1. 대시보드 수치는 자동 갱신 스크립트 기준값을 단일 소스로 본다.
2. 수동 수정 금지(체크박스 수정 후 스크립트 실행으로만 갱신).
3. PR/커밋 시 본 문서 상단 대시보드 갱신 여부를 리뷰 체크 항목으로 포함한다.

## 6) 변경 로그

- 2026-03-01: 로드맵 문서를 개발진행 대시보드 형태로 개편.
- 2026-03-01: W3_006 적용 계획을 즉시적용/조건부적용 Track으로 분리.
- 2026-03-01: `/query` feature flag 기반 추적 로그(`DOC_RAG_QUERY_TRACE_ENABLED`) 1차 적용.
- 2026-03-02: `/query` 응답에 citation(`sources[]`) 필드 추가.
- 2026-03-02: 메타데이터 호환 확장(`year_text`, `scientist`, `source_file`, `topic`) 및 업로드/인덱싱 optional 규칙 반영.
- 2026-03-04: 오답노트 수집 포맷(`query_failure_notes.jsonl`) 도입 및 API/프론트 계약 테스트, 운영 문서 동기화 반영.
