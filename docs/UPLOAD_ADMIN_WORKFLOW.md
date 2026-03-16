# Upload/Admin Workflow Design (2026-03-17)

## 목적
- 업로드 요청 생성, 관리자 승인/반려, 문서 갱신(update)까지의 운영 절차를 고정한다.
- 현재 구현의 한계를 명확히 드러내고, 다음 구현 단계가 무엇을 바꿔야 하는지 기준을 남긴다.

## 현재 구현 상태
- 일반 사용자는 `POST /upload-requests`로 요청을 만들 수 있다.
- 관리자는 `/admin`에서 `pending/approved/rejected` 목록을 보고 승인/반려할 수 있다.
- 승인 시 현재는 요청 내용을 바로 벡터스토어에 추가한다.
- 반려 시 현재는 `rejected_reason`만 저장한다.

## 현재 구현의 핵심 갭
1. 승인된 업로드가 파일 기반 원본으로 보존되지 않는다.
2. 전체 `reindex`를 다시 돌리면 승인 업로드가 재구성되지 않는다.
3. `GET /rag-docs`는 기본 `data/*.md`만 보여 주므로 승인 업로드와 운영 문서가 분리돼 있다.
4. 요청이 "신규 문서"인지 "기존 문서 갱신"인지 구분되지 않는다.
5. 업데이트 전후 비교, 버전 이력, 롤백 기준이 없다.
6. `auto-approve`가 update까지 열리면 운영자가 모르는 사이 기존 문서를 덮어쓸 위험이 있다.

## 설계 원칙
1. 벡터스토어가 아니라 승인된 Markdown 원본이 운영 기준 데이터다.
2. repo의 `data/*.md` seed 문서는 그대로 두고, 운영 중 승인된 문서는 별도 runtime 저장소에 둔다.
3. 신규와 갱신은 같은 큐에서 처리하되 요청 타입을 명확히 구분한다.
4. 상태 모델은 MVP 범위에서 `pending/approved/rejected`를 유지하고, 필요한 이력은 metadata로 남긴다.
5. update는 항상 관리자 승인 경로를 거친다. `auto-approve`는 신규 문서에만 제한적으로 허용한다.

## 운영 데이터 모델 결정

### 1) 문서 원본 저장소
- seed 문서:
  - 현재처럼 repo의 `data/*.md`
- managed 문서:
  - 새 경로: `chroma_db/managed_docs/`
  - 이유:
    - 로컬 운영 산출물을 git 추적 대상에서 분리할 수 있다.
    - 현재 local persistence 경로(`chroma_db`)와 동일한 운영 모델을 유지할 수 있다.

### 2) 논리 문서 단위
- `source_name`은 파일명이고, `doc_key`는 논리 문서 식별자다.
- 예시:
  - seed 문서 `fr.md`의 `doc_key`는 `fr`
  - 새 관리 문서 `fr_university_update_2026-03.md`도 `doc_key=fr`이면 기존 프랑스 문서의 갱신으로 본다.
- `GET /rag-docs`와 reindex 기준은 "활성(active) 버전의 `doc_key` 목록"으로 본다.

### 3) 요청 타입
- `create`: 새 논리 문서 생성
- `update`: 기존 `doc_key`의 활성 버전을 교체

요청에 추가할 필드:
- `request_type`
- `doc_key`
- `change_summary`
- `target_doc_key` 또는 기존 활성 문서 참조
- `decision_note`

## 상태와 전이

| status | 의미 | 다음 액션 |
| --- | --- | --- |
| `pending` | 검토 대기 | 관리자 승인 또는 반려 |
| `approved` | 승인 및 활성 버전 반영 완료 | 조회/이력 확인 |
| `rejected` | 반려 완료 | 수정 후 새 요청 재제출 |

보조 필드:
- `approved_at`
- `rejected_at`
- `reviewed_by`
- `decision_note`
- `active_version`
- `superseded_version`

## 워크플로우

### A. 신규 문서 등록
1. 사용자는 `content`, `collection`, `source_name`, `doc_key`, `change_summary`를 제출한다.
2. 서버는 markdown validation과 `doc_key/source_name` 중복 여부를 계산한다.
3. 요청은 `pending`으로 큐에 들어간다.
4. 관리자는 validation 결과와 중복 힌트를 보고 승인/반려한다.
5. 승인되면:
   - managed 문서를 runtime 저장소에 버전 파일로 저장
   - 해당 `doc_key`의 active 포인터를 새 버전으로 전환
   - 영향 컬렉션만 재인덱싱 또는 부분 갱신
6. 반려되면 reason code + 자유 메모를 남긴다.

### B. 기존 문서 갱신
1. 사용자는 `request_type=update`, `doc_key`, 새 본문, `change_summary`를 제출한다.
2. 서버는 현재 active 문서를 찾아 diff 대상과 validation 정보를 요청에 붙인다.
3. 관리자는 기존 active 버전과 요청 버전을 비교해 승인/반려한다.
4. 승인되면:
   - 기존 active 버전은 history로 남기고 새 버전을 active로 전환
   - 재인덱싱 시 seed 문서보다 managed active 버전이 우선한다
5. 반려되면:
   - 기존 active 버전은 그대로 유지
   - 요청만 `rejected`로 닫는다

### C. 재제출과 롤백
- 재제출:
  - 반려된 요청을 직접 수정하는 대신 새 요청으로 다시 제출한다.
  - 필요하면 `supersedes_request_id`만 연결한다.
- 롤백:
  - 1차 구현에서는 별도 버튼보다 "이전 active 버전을 새 update 요청으로 재등록"하는 운영 절차를 기본으로 둔다.
  - 전용 rollback API는 이력이 쌓인 뒤 필요성이 확인되면 추가한다.

## API/UI 설계 방향

### API
- 유지:
  - `GET /upload-requests`
  - `GET /upload-requests/{id}`
  - `POST /upload-requests`
  - `POST /upload-requests/{id}/approve`
  - `POST /upload-requests/{id}/reject`
- 확장:
  - 요청 생성 시 `request_type`, `doc_key`, `change_summary`
  - 승인 응답에 `active_doc`, `superseded_doc`, `reindex_scope`
  - 반려 응답에 `reason_code`, `decision_note`
  - 문서 목록 응답에 `origin=seed|managed`, `doc_key`, `active_version`

### 관리자 UI
- 기본 필터는 `pending`
- 각 요청에서 바로 보여야 하는 것:
  - request type
  - doc_key / source_name
  - target collection
  - validation usable/reasons/warnings
  - change summary
  - 기존 active 문서 존재 여부
- 1차 UI는 표 + detail pane 기준으로 유지한다.
- diff 뷰는 전체 텍스트 라인 diff 대신 "기존 문서 미리보기 / 제안 문서 미리보기" 2열 비교부터 시작한다.

## 자동 승인 정책
- `DOC_RAG_AUTO_APPROVE`는 계속 개인 운영용 옵션으로만 둔다.
- 적용 범위:
  - 허용: `create` + validation 통과 + 기존 `doc_key` 충돌 없음
  - 금지: `update`, 충돌 의심 요청, validation 실패 요청

## 구현 우선순위

### Slice 1
- managed 문서 runtime 저장소 추가
- `doc_key` / `request_type` / `change_summary` 필드 추가
- `GET /rag-docs`가 seed + managed active 문서를 함께 반환
- 승인된 신규/갱신 요청이 full reindex 후에도 유지되게 만들기

### Slice 2
- 관리자 상세 보기 강화
- pending 기본 필터, update 강조, change summary 노출
- reject reason code 정리

### Slice 3
- 버전 이력 조회
- rollback 보조 UX
- diff 요약 자동화

## 완료 기준
- 승인된 요청은 벡터스토어가 아니라 managed markdown 원본으로 재구성 가능해야 한다.
- 신규와 갱신이 관리자 큐에서 명확히 구분돼야 한다.
- full reindex 후에도 active 문서 집합이 유지돼야 한다.
- `/rag-docs`, `/admin`, reindex 동작이 같은 문서 기준을 봐야 한다.
