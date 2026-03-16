# Desktop Wrapper PoC Report (2026-03-17)

## 목적
- 현재 FastAPI + 브라우저 UI 구조를 데스크톱 앱으로 감쌀 수 있는지 확인한다.
- MVP 본체에 포함할지, 제품화 후속 검토로 보류할지 판단 기준을 남긴다.

## 범위
- Tauri와 Electron 중 즉시 실행 가능한 경로를 비교한다.
- 기존 웹 UI(`/intro`, `/app`, `/admin`)를 재작성하지 않고 재사용한다.
- 로컬 Python 런타임으로 `app_api.py`를 띄우고 `/health` 준비 이후 데스크톱 창에 연결한다.

## 이번 세션 구현
- PoC 경로: `desktop/electron`
- 추가 파일:
  - `desktop/electron/main.js`
  - `desktop/electron/server_runtime.js`
  - `desktop/electron/scripts/smoke_runtime.js`
  - `desktop/electron/package.json`
- 동작:
  - 기존 서버가 이미 떠 있으면 그대로 attach
  - 서버가 없으면 `.venv/bin/python` 또는 시스템 `python3/python`으로 `app_api.py` 실행
  - `/health` 응답이 준비되면 Electron 창에서 `/intro` 로드
  - 앱 종료 시 Electron이 직접 띄운 Python 프로세스는 같이 정리

## Electron 선택 이유
- 이번 작업 환경에는 `node`/`npm`이 있었고 바로 실행/검증이 가능했다.
- `cargo`가 없어 Tauri는 즉시 실행 PoC 기준으로 준비 비용이 더 컸다.
- 현재 앱은 이미 웹 UI가 있으므로, 데스크톱 PoC는 "웹을 감싸는 셸"이 가장 작은 변경 경로다.

## 검증
- 정적 검증:
  - `cd desktop/electron && npm run check`
- 런타임 검증:
  - `cd desktop/electron && npm run smoke`
  - 결과: `ready mode=spawned url=http://127.0.0.1:8000/intro vectors=37 chunking=char`
- 회귀 검증:
  - `.venv/bin/python -m pytest -q`
  - 결과: `32 passed in 4.81s`

참고:
- sandbox 안에서는 로컬 포트 bind가 막혀 `npm run smoke`, Playwright E2E가 실패했다.
- 동일 명령을 로컬 권한으로 재실행했을 때는 정상 통과했다.

## 이번 PoC에서 확인된 것

### 가능한 것
1. 기존 FastAPI + 웹 UI를 거의 그대로 유지한 채 데스크톱 셸을 붙일 수 있다.
2. Python 서버 시작, `/health` readiness 대기, intro/app/admin 라우트 진입까지 하나의 앱 흐름으로 감쌀 수 있다.
3. 이미 떠 있는 서버 attach와 Electron이 직접 띄운 서버 lifecycle 관리 둘 다 최소 수준으로 가능하다.

### 아직 남은 리스크
1. 현재 PoC는 여전히 Python 가상환경, Python 패키지, Ollama/모델 준비 상태에 의존한다.
2. "설치 가능한 데스크톱 앱"으로 가려면 embedded Python 또는 별도 설치 전략이 필요하다.
3. Electron 번들 크기와 플랫폼별 패키징/서명/업데이트 전략은 아직 검증하지 않았다.
4. 포트 충돌, 모델 미실행, 오프라인 임베딩 경로 누락 같은 운영 실패는 여전히 런타임 준비도에 좌우된다.
5. 관리 워크플로우와 운영 가이드가 정리되기 전 데스크톱 배포를 먼저 강화하면 제품 표면만 넓어질 수 있다.

## MVP 반영 판단
- 결론: MVP 본체에는 넣지 않고 보류한다.
- 이유:
  - 현재 MVP의 기본 경로는 웹 UI 기반 로컬 RAG이며 이미 동작한다.
  - 이번 PoC는 "래핑이 가능하다"는 기술 검증에는 충분하지만, 배포/설치/운영 단순화까지 해결하지는 못했다.
  - 지금 우선순위는 데스크톱 셸보다 업로드/갱신 관리자 워크플로우 정리 쪽이 운영 가치가 더 크다.

## 다음 액션
1. `TODO.md` / `NEXT_SESSION_PLAN.md` 기준 즉시 다음 항목은 문서 업로드/갱신 관리자 워크플로우 설계다.
2. 데스크톱 경로를 다시 잡을 때는 "embedded Python vs 별도 설치 요구"를 먼저 결정한다.
3. 그 다음 단계에서만 패키징(`electron-builder` 등), 로그 뷰어, preflight UI, auto-update 여부를 검토한다.
