# doc_rag Desktop Launcher

`desktop/electron`은 `trunk_rag`의 기존 FastAPI + 웹 UI를 감싸는 선택형 데스크톱 런처입니다.

중요:
- 정식 설치형 제품이 아닙니다.
- 현재 목적은 "브라우저 대신 앱 창으로 열기"와 "preflight -> 서버 시작 -> `/intro` 진입" 자동화입니다.
- Python, Python 의존성, 로컬 LLM/Ollama, 임베딩 준비 상태는 여전히 필요합니다.

## Quick Start

Windows:

```powershell
cd <repo>\desktop\electron
npm install
cd <repo>
.\run_doc_rag_desktop.bat
```

직접 실행:

```powershell
cd <repo>\desktop\electron
npm run check
npm run preflight
npm start
```

## 동작 방식

1. 시작 전에 preflight로 repo 경로, Python, backend import, 기본 LLM 런타임 상태를 점검합니다.
2. 기존 서버가 이미 떠 있으면 그대로 attach합니다.
3. 서버가 없으면 `.venv` 또는 시스템 Python으로 `app_api.py`를 실행합니다.
4. `/health`가 준비되면 Electron 창에서 `/intro`를 엽니다.
5. Electron이 직접 띄운 서버는 앱 종료 시 함께 정리합니다.

## 현재 한계

- 패키징/배포 하드닝은 아직 하지 않습니다.
- `embedded Python` 또는 `별도 설치 요구` 전략이 확정되기 전까지 설치 파일 생성은 보류합니다.
- 이 경로는 현재 "선택형 런처"이지 배포 완료된 데스크톱 앱이 아닙니다.
